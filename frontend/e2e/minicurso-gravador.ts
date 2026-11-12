import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import type { Browser, BrowserContext, Locator, Page } from '@playwright/test'
import { installDemoApi } from './minicurso-demo-api'

/**
 * Gravador das aulas do Minicurso FiscWise.
 *
 * O vídeo do Playwright não mostra o mouse, então a página ganha um cursor
 * desenhado (segue os eventos reais de mouse), um efeito de clique e uma
 * legenda com o passo atual. Cada aula abre com um cartão de título, que
 * também vira a capa. No fim o .webm vira .mp4 (H.264) em public/minicurso/
 * e a duração e os capítulos vão para src/lib/minicursoGravacoes.json.
 */

const ROOT = process.cwd()
const OUT_DIR = path.join(ROOT, 'public', 'minicurso')
const RAW_DIR = path.join(ROOT, 'test-results', 'minicurso-bruto')
const JSON_PATH = path.join(ROOT, 'src', 'lib', 'minicursoGravacoes.json')
const SIZE = { width: 1280, height: 720 }

const OVERLAY_SCRIPT = () => {
  const install = () => {
    if (document.getElementById('mc-cursor')) return
    const style = document.createElement('style')
    style.textContent = `
      #mc-cursor{position:fixed;left:0;top:0;width:26px;height:26px;z-index:2147483646;pointer-events:none;
        transform:translate(-3px,-2px);transition:none;filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))}
      .mc-ripple{position:fixed;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;z-index:2147483645;
        pointer-events:none;background:rgba(224,94,24,.35);border:2px solid rgba(224,94,24,.9);animation:mc-r .55s ease-out forwards}
      @keyframes mc-r{from{transform:scale(.3);opacity:1}to{transform:scale(1.25);opacity:0}}
      #mc-caption{position:fixed;left:50%;bottom:22px;transform:translateX(-50%);z-index:2147483644;pointer-events:none;
        max-width:900px;padding:12px 20px;border-radius:12px;background:rgba(26,37,64,.94);color:#fff;
        font:500 19px/1.35 'Geist Variable',system-ui,sans-serif;box-shadow:0 8px 24px rgba(0,0,0,.25);
        display:none;align-items:center;gap:12px;white-space:nowrap}
      #mc-caption.top{bottom:auto;top:70px}
      #mc-caption b{display:inline-flex;align-items:center;justify-content:center;min-width:30px;height:30px;padding:0 8px;border-radius:999px;
        background:#e05e18;font-weight:600;font-size:15px}
      #mc-card{position:fixed;inset:0;z-index:2147483647;display:none;flex-direction:column;justify-content:center;
        padding:0 110px;background:#1A2540;color:#fff;font-family:'Geist Variable',system-ui,sans-serif}
      #mc-card .k{display:flex;align-items:center;gap:12px;font-size:20px;font-weight:500;color:#f3a57a}
      #mc-card .k i{display:inline-block;width:34px;height:34px;border-radius:8px;background:#e05e18}
      #mc-card h1{margin:22px 0 14px;font-size:62px;line-height:1.08;font-weight:600;letter-spacing:-.02em;max-width:980px}
      #mc-card p{margin:0;font-size:24px;line-height:1.45;color:#c9d1e3;max-width:900px}
      #mc-card .bar{position:absolute;left:110px;bottom:84px;width:120px;height:6px;border-radius:3px;background:#e05e18}`
    document.head.appendChild(style)
    const cursor = document.createElement('div')
    cursor.id = 'mc-cursor'
    cursor.innerHTML =
      '<svg viewBox="0 0 24 24" width="26" height="26"><path d="M3 2l7.5 19 2.6-7.9L21 10.5z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>'
    const saved = sessionStorage.getItem('mc-pos')
    const [x, y] = saved ? saved.split(',').map(Number) : [640, 360]
    cursor.style.left = `${x}px`
    cursor.style.top = `${y}px`
    document.body.appendChild(cursor)
    const caption = document.createElement('div')
    caption.id = 'mc-caption'
    document.body.appendChild(caption)
    const card = document.createElement('div')
    card.id = 'mc-card'
    document.body.appendChild(card)
    document.addEventListener(
      'mousemove',
      (e) => {
        cursor.style.left = `${e.clientX}px`
        cursor.style.top = `${e.clientY}px`
        sessionStorage.setItem('mc-pos', `${e.clientX},${e.clientY}`)
      },
      true,
    )
    document.addEventListener(
      'mousedown',
      (e) => {
        const r = document.createElement('div')
        r.className = 'mc-ripple'
        r.style.left = `${e.clientX}px`
        r.style.top = `${e.clientY}px`
        document.body.appendChild(r)
        setTimeout(() => r.remove(), 600)
      },
      true,
    )
  }
  if (document.body) install()
  else document.addEventListener('DOMContentLoaded', install)
}

export interface LessonMeta {
  id: string
  title: string
  subtitle: string
}

export class Recorder {
  readonly page: Page
  private context: BrowserContext
  private pageStartedAt: number
  private lessonStartedAt = 0
  private chapters: Array<{ t: number; label: string }> = []
  private step = 0
  private mouse = { x: 640, y: 360 }

  private constructor(context: BrowserContext, page: Page, private meta: LessonMeta) {
    this.context = context
    this.page = page
    this.pageStartedAt = Date.now()
  }

  static async open(browser: Browser, meta: LessonMeta, opts: { colorScheme?: 'light' | 'dark' } = {}) {
    mkdirSync(RAW_DIR, { recursive: true })
    const context = await browser.newContext({
      viewport: SIZE,
      deviceScaleFactor: 1,
      locale: 'pt-BR',
      timezoneId: 'America/Sao_Paulo',
      serviceWorkers: 'block',
      colorScheme: opts.colorScheme ?? 'light',
      recordVideo: { dir: RAW_DIR, size: SIZE },
    })
    await installDemoApi(context)
    await context.addInitScript(OVERLAY_SCRIPT)
    const page = await context.newPage()
    return new Recorder(context, page, meta)
  }

  /** Abre a rota e espera a tela assentar (sem spinners). */
  async goto(route: string) {
    await this.page.goto(route)
    await this.page.waitForLoadState('networkidle').catch(() => undefined)
    await this.page.waitForTimeout(600)
  }

  /** Cartão de abertura (também a capa da aula). Marca o início do vídeo final. */
  async titleCard(ms = 3200) {
    await this.page.evaluate(({ title, subtitle }) => {
      const card = document.getElementById('mc-card')!
      card.innerHTML = `<div class="k"><i></i>Minicurso FiscWise</div><h1>${title}</h1><p>${subtitle}</p><div class="bar"></div>`
      card.style.display = 'flex'
    }, this.meta)
    await this.page.waitForTimeout(150)
    this.lessonStartedAt = Date.now()
    await this.page.waitForTimeout(ms)
    await this.page.evaluate(() => {
      document.getElementById('mc-card')!.style.display = 'none'
    })
  }

  /** Cartão final. */
  async endCard(text: string, ms = 3000) {
    await this.caption(null)
    await this.page.evaluate((t) => {
      const card = document.getElementById('mc-card')!
      card.innerHTML = `<div class="k"><i></i>Minicurso FiscWise</div><h1>Pronto!</h1><p>${t}</p><div class="bar"></div>`
      card.style.display = 'flex'
    }, text)
    await this.page.waitForTimeout(ms)
  }

  /** Novo passo: vira capítulo do vídeo e aparece como legenda. */
  async chapter(label: string, pauseMs = 900) {
    this.step += 1
    const t = Math.max(0, Math.round(((Date.now() - this.lessonStartedAt) / 1000) * 10) / 10)
    this.chapters.push({ t, label })
    await this.page.evaluate((top) => document.getElementById('mc-caption')?.classList.toggle('top', top), this.mouse.y > SIZE.height - 170)
    await this.caption(label, this.step)
    await this.page.waitForTimeout(pauseMs)
  }

  async caption(text: string | null, step?: number) {
    await this.page.evaluate(
      ({ text, step }) => {
        const el = document.getElementById('mc-caption')
        if (!el) return
        if (!text) {
          el.style.display = 'none'
          return
        }
        el.innerHTML = `${step ? `<b>${step}</b>` : ''}<span></span>`
        el.querySelector('span')!.textContent = text
        el.style.display = 'flex'
      },
      { text, step },
    )
  }

  /** Põe a legenda no topo se o elemento estiver na parte de baixo da tela. */
  async avoid(target: Locator) {
    const box = await target.boundingBox().catch(() => null)
    const low = !!box && box.y + box.height > SIZE.height - 120
    await this.page.evaluate((top) => document.getElementById('mc-caption')?.classList.toggle('top', top), low)
  }

  async wait(ms: number) {
    await this.page.waitForTimeout(ms)
  }

  /** Move o mouse com aceleração suave até o centro do elemento. */
  async moveTo(target: Locator, opts: { dx?: number; dy?: number; ms?: number } = {}) {
    await target.scrollIntoViewIfNeeded({ timeout: 10_000 })
    const box = await target.boundingBox()
    if (!box) throw new Error('Elemento sem posição na tela')
    const x = box.x + Math.min(box.width / 2, opts.dx ?? box.width / 2)
    const y = box.y + (opts.dy ?? box.height / 2)
    // Legenda sobe quando o alvo fica embaixo, para não cobrir o botão.
    await this.page.evaluate((top) => document.getElementById('mc-caption')?.classList.toggle('top', top), y > SIZE.height - 170)
    await this.moveToPoint(x, y, opts.ms)
  }

  async moveToPoint(x: number, y: number, ms?: number) {
    const from = { ...this.mouse }
    const dist = Math.hypot(x - from.x, y - from.y)
    const duration = ms ?? Math.min(1100, Math.max(350, dist * 1.1))
    const frames = Math.max(8, Math.round(duration / 16))
    for (let i = 1; i <= frames; i++) {
      const p = i / frames
      const e = p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2
      await this.page.mouse.move(from.x + (x - from.x) * e, from.y + (y - from.y) * e)
      await this.page.waitForTimeout(16)
    }
    this.mouse = { x, y }
  }

  async click(target: Locator, opts: { dx?: number; after?: number } = {}) {
    await this.moveTo(target, { dx: opts.dx })
    await this.page.waitForTimeout(220)
    await this.page.mouse.down()
    await this.page.waitForTimeout(90)
    await this.page.mouse.up()
    await this.page.waitForTimeout(opts.after ?? 700)
  }

  async hover(target: Locator, ms = 900) {
    await this.moveTo(target)
    await this.page.waitForTimeout(ms)
  }

  async type(target: Locator, text: string, opts: { delay?: number; after?: number } = {}) {
    await this.click(target, { after: 250 })
    await this.page.keyboard.type(text, { delay: opts.delay ?? 65 })
    await this.page.waitForTimeout(opts.after ?? 500)
  }

  async select(target: Locator, label: string) {
    await this.moveTo(target)
    await this.page.waitForTimeout(200)
    await this.page.mouse.down()
    await this.page.mouse.up()
    await target.selectOption({ label })
    await this.page.waitForTimeout(700)
  }

  /** Fecha o contexto, converte o vídeo e registra duração e capítulos. */
  async finish() {
    const video = this.page.video()
    const offset = Math.max(0, (this.lessonStartedAt - this.pageStartedAt) / 1000)
    const duration = Math.round(((Date.now() - this.lessonStartedAt) / 1000) * 10) / 10
    await this.context.close()
    if (!video) throw new Error('Gravação de vídeo desligada')
    const raw = await video.path()
    mkdirSync(OUT_DIR, { recursive: true })
    const mp4 = path.join(OUT_DIR, `${this.meta.id}.mp4`)
    const jpg = path.join(OUT_DIR, `${this.meta.id}.jpg`)
    execFileSync('ffmpeg', [
      '-y', '-loglevel', 'error', '-ss', offset.toFixed(2), '-i', raw,
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '26', '-tune', 'stillimage',
      '-pix_fmt', 'yuv420p', '-r', '25', '-movflags', '+faststart', '-an', mp4,
    ])
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-ss', '1.5', '-i', mp4, '-frames:v', '1', '-vf', 'scale=640:-2', '-q:v', '4', jpg])
    const all = existsSync(JSON_PATH) ? (JSON.parse(readFileSync(JSON_PATH, 'utf8')) as Record<string, unknown>) : {}
    all[this.meta.id] = { duration, chapters: this.chapters }
    const sorted = Object.fromEntries(Object.entries(all).sort(([a], [b]) => a.localeCompare(b)))
    writeFileSync(JSON_PATH, `${JSON.stringify(sorted, null, 2)}\n`)
  }
}

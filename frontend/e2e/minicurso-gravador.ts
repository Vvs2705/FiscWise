import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import type { Browser, BrowserContext, Locator, Page } from '@playwright/test'
import { installDemoApi } from './minicurso-demo-api'
import { ROTEIRO } from './minicurso-roteiro'

/**
 * Gravador das aulas do Minicurso FiscWise.
 *
 * O vídeo do Playwright não mostra o mouse, então a página ganha um cursor
 * desenhado (segue os eventos reais de mouse) e um efeito de clique. Cada aula
 * abre com um cartão de título, que também vira a capa.
 *
 * Narração: cada `chapter()` toca a próxima fala do roteiro
 * (e2e/minicurso-roteiro.ts, áudio em e2e/minicurso-audio/<aula>-<n>.mp3) e o
 * capítulo seguinte só começa quando a fala anterior termina, então a tela
 * acompanha a voz. As falas viram legendas (cues) que a página do Minicurso
 * mostra por cima do vídeo, no tamanho que a pessoa escolher.
 *
 * Zoom: ao clicar, digitar ou selecionar, a "câmera" aproxima do alvo e depois
 * volta. O zoom é aplicado na edição (ffmpeg), não na página, para não mexer
 * em layout, modais e popovers.
 *
 * No fim o .webm vira .mp4 (H.264 + AAC com voz e trilha) em public/minicurso/
 * e duração, capítulos e legendas vão para src/lib/minicursoGravacoes.json.
 */

const ROOT = process.cwd()
const OUT_DIR = path.join(ROOT, 'public', 'minicurso')
const RAW_DIR = path.join(ROOT, 'test-results', 'minicurso-bruto')
const JSON_PATH = path.join(ROOT, 'src', 'lib', 'minicursoGravacoes.json')
const AUDIO_DIR = path.join(ROOT, 'e2e', 'minicurso-audio')
const MUSIC = path.join(AUDIO_DIR, 'musica.mp3')
const SIZE = { width: 1280, height: 720 }
const FPS = 25
/** Duração da aproximação/afastamento da câmera, em segundos. */
const RAMP = 0.5
const ZOOM_CLICK = 1.6
const ZOOM_HOVER = 1.35

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
      #mc-file{position:fixed;right:36px;bottom:36px;z-index:2147483644;pointer-events:none;display:none;width:520px;
        border-radius:14px;background:#fff;color:#1A2540;box-shadow:0 18px 48px rgba(10,20,40,.35);overflow:hidden;
        font:13px/1.4 'Geist Variable',system-ui,sans-serif;animation:mc-in .35s ease-out}
      @keyframes mc-in{from{transform:translateY(16px);opacity:0}to{transform:none;opacity:1}}
      #mc-file header{display:flex;align-items:center;gap:10px;padding:12px 16px;background:#1A2540;color:#fff;font-weight:600;font-size:15px}
      #mc-file header i{display:inline-flex;align-items:center;justify-content:center;width:34px;height:22px;border-radius:5px;
        background:#1f8f4e;font-style:normal;font-size:11px;font-weight:700}
      #mc-file table{width:100%;border-collapse:collapse}
      #mc-file th,#mc-file td{padding:6px 10px;border-bottom:1px solid #e6e9f0;text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:170px}
      #mc-file th{background:#f4f6fa;font-weight:600;font-size:12px;color:#4a5878}
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
    const file = document.createElement('div')
    file.id = 'mc-file'
    document.body.appendChild(file)
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

interface Cue {
  start: number
  end: number
  text: string
}

interface ZoomKey {
  t: number
  z: number
  cx: number
  cy: number
}

const round1 = (n: number) => Math.round(n * 10) / 10

function probeDuration(file: string): number {
  const out = execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', file])
  return Number(String(out).trim())
}

/** Quebra a fala em frases curtas para a legenda (no máximo ~95 caracteres). */
function splitCaption(text: string): string[] {
  const parts: string[] = []
  for (const sentence of text.split(/(?<=[.!?])\s+/)) {
    if (sentence.length <= 95) {
      parts.push(sentence)
      continue
    }
    // Frase longa: corta na vírgula ou dois-pontos mais perto do meio.
    const mid = sentence.length / 2
    let best = -1
    for (let i = 0; i < sentence.length; i++) {
      if ((sentence[i] === ',' || sentence[i] === ':') && (best < 0 || Math.abs(i - mid) < Math.abs(best - mid))) best = i
    }
    if (best < 0) parts.push(sentence)
    else parts.push(sentence.slice(0, best + 1), sentence.slice(best + 1).trim())
  }
  return parts.filter(Boolean)
}

/** Expressão ffmpeg que interpola `prop` entre os keyframes com easing suave. */
function keyframeExpr(keys: ZoomKey[], prop: 'z' | 'cx' | 'cy', T: string): string {
  let expr = String(keys[keys.length - 1][prop])
  for (let i = keys.length - 2; i >= 0; i--) {
    const a = keys[i]
    const b = keys[i + 1]
    if (b.t <= a.t) continue
    const u = `clip((${T}-${a.t.toFixed(3)})/${(b.t - a.t).toFixed(3)},0,1)`
    const seg = a[prop] === b[prop] ? String(a[prop]) : `${a[prop]}+(${b[prop] - a[prop]})*${u}*${u}*(3-2*${u})`
    expr = `if(lt(${T},${b.t.toFixed(3)}),${seg},${expr})`
  }
  return expr
}

export class Recorder {
  readonly page: Page
  private context: BrowserContext
  private pageStartedAt: number
  private lessonStartedAt = 0
  private chapters: Array<{ t: number; label: string }> = []
  private cues: Cue[] = []
  private narration: Array<{ t: number; file: string }> = []
  private speechEndsAt = 0
  private step = 0
  private mouse = { x: 640, y: 360 }
  private zoomKeys: ZoomKey[] = [{ t: 0, z: 1, cx: 640, cy: 360 }]
  private zoom: Omit<ZoomKey, 't'> = { z: 1, cx: 640, cy: 360 }
  private zoomRelease: number | null = null
  private clips: Array<{ file: string; duration: number }>

  private constructor(context: BrowserContext, page: Page, private meta: LessonMeta) {
    this.context = context
    this.page = page
    this.pageStartedAt = Date.now()
    const falas = ROTEIRO[meta.id]
    if (!falas) throw new Error(`Aula ${meta.id} sem roteiro em minicurso-roteiro.ts`)
    this.clips = falas.map((_, i) => {
      const file = path.join(AUDIO_DIR, `${meta.id}-${i + 1}.mp3`)
      if (!existsSync(file)) throw new Error(`Falta a narração ${file}. Gere a voz da aula e corte nas pausas.`)
      return { file, duration: probeDuration(file) }
    })
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

  /** Segundos desde o início do vídeo final (cartão de título). */
  private now() {
    return this.lessonStartedAt ? (Date.now() - this.lessonStartedAt) / 1000 : 0
  }

  /** Abre a rota e espera a tela assentar (sem spinners). */
  async goto(route: string) {
    await this.page.goto(route)
    await this.page.waitForLoadState('networkidle').catch(() => undefined)
    await this.page.waitForTimeout(600)
  }

  /** Cartão de abertura (também a capa da aula). Marca o início do vídeo final. */
  async titleCard(ms = 3600) {
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

  /** Cartão final, depois que a narração termina. */
  async endCard(text: string, ms = 4000) {
    await this.waitSpeech(500)
    await this.flushZoom(true)
    await this.page.evaluate((t) => {
      const card = document.getElementById('mc-card')!
      card.innerHTML = `<div class="k"><i></i>Minicurso FiscWise</div><h1>Pronto!</h1><p>${t}</p><div class="bar"></div>`
      card.style.display = 'flex'
    }, text)
    await this.page.waitForTimeout(ms)
  }

  /** Espera a fala atual terminar (mais uma folga). */
  async waitSpeech(gapMs = 350) {
    const left = this.speechEndsAt - Date.now()
    if (left > -gapMs) await this.page.waitForTimeout(left + gapMs)
  }

  /**
   * Próximo capítulo do roteiro: espera a fala anterior acabar, começa a nova
   * fala e registra capítulo e legendas. As ações seguintes acontecem enquanto
   * a narradora fala.
   */
  async chapter(pauseMs = 500) {
    await this.waitSpeech()
    const cap = ROTEIRO[this.meta.id][this.step]
    const clip = this.clips[this.step]
    if (!cap || !clip) throw new Error(`Aula ${this.meta.id}: capítulo ${this.step + 1} não existe no roteiro`)
    this.step += 1
    const t = this.now()
    this.chapters.push({ t: round1(t), label: cap.label })
    this.narration.push({ t, file: clip.file })
    // Legendas: frases distribuídas pelo tempo da fala, proporcional ao tamanho.
    const parts = splitCaption(cap.fala)
    const speaking = Math.max(0.5, clip.duration - 0.3)
    const total = parts.reduce((n, p) => n + p.length, 0)
    let at = t
    for (const text of parts) {
      const len = (speaking * text.length) / total
      this.cues.push({ start: round1(at), end: round1(at + len + 0.25), text })
      at += len
    }
    this.speechEndsAt = Date.now() + clip.duration * 1000
    await this.page.waitForTimeout(pauseMs)
  }

  /** Mostra um "arquivo" (ex.: o CSV que vai ser importado) no canto da tela. */
  async showFile(name: string, rows: string[][], ms = 2500) {
    await this.page.evaluate(
      ({ name, rows }) => {
        const el = document.getElementById('mc-file')!
        const esc = (s: string) => s.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]!)
        const [head, ...body] = rows
        el.innerHTML =
          `<header><i>CSV</i>${esc(name)}</header><table><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join('')}</tr></thead>` +
          `<tbody>${body.map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table>`
        el.style.display = 'block'
      },
      { name, rows },
    )
    await this.page.waitForTimeout(ms)
  }

  async hideFile() {
    await this.page.evaluate(() => {
      document.getElementById('mc-file')!.style.display = 'none'
    })
  }

  async wait(ms: number) {
    await this.page.waitForTimeout(ms)
  }

  // --- câmera -------------------------------------------------------------

  private pushKey(t: number) {
    const last = this.zoomKeys[this.zoomKeys.length - 1]
    this.zoomKeys.push({ t: Math.max(t, last.t), ...this.zoom })
  }

  /** Afasta a câmera se a última aproximação já "esfriou" (ou sempre, com force). */
  private async flushZoom(force = false) {
    if (this.zoomRelease === null) return
    if (!force && this.now() - this.zoomRelease < 1.1) return
    this.pushKey(this.zoomRelease)
    this.zoom = { ...this.zoom, z: 1 }
    this.pushKey(this.zoomRelease + RAMP)
    this.zoomRelease = null
    if (force) await this.page.waitForTimeout(RAMP * 1000)
  }

  /** Aproxima a câmera do ponto (ou passeia até ele, se já estiver perto). */
  private async zoomTo(cx: number, cy: number, z: number) {
    if (!this.lessonStartedAt) return
    await this.flushZoom()
    this.zoomRelease = null
    const t = this.now()
    this.pushKey(t)
    this.zoom = { z, cx: Math.round(cx), cy: Math.round(cy) }
    this.pushKey(t + RAMP)
    await this.page.waitForTimeout(RAMP * 1000)
  }

  /** Marca que a ação terminou: a câmera volta, a não ser que outra ação venha logo. */
  private releaseZoom() {
    this.zoomRelease = this.now()
  }

  // --- mouse --------------------------------------------------------------

  /** Move o mouse com aceleração suave até o centro do elemento. */
  async moveTo(target: Locator, opts: { dx?: number; dy?: number; ms?: number } = {}) {
    await target.scrollIntoViewIfNeeded({ timeout: 10_000 })
    const box = await target.boundingBox()
    if (!box) throw new Error('Elemento sem posição na tela')
    const x = box.x + Math.min(box.width / 2, opts.dx ?? box.width / 2)
    const y = box.y + (opts.dy ?? box.height / 2)
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

  async click(target: Locator, opts: { dx?: number; after?: number; zoom?: number | false } = {}) {
    await this.moveTo(target, { dx: opts.dx })
    if (opts.zoom !== false) await this.zoomTo(this.mouse.x, this.mouse.y, opts.zoom ?? ZOOM_CLICK)
    await this.page.waitForTimeout(220)
    await this.page.mouse.down()
    await this.page.waitForTimeout(90)
    await this.page.mouse.up()
    await this.page.waitForTimeout(Math.min(opts.after ?? 700, 900))
    if (opts.zoom !== false) this.releaseZoom()
    if ((opts.after ?? 700) > 900) await this.page.waitForTimeout((opts.after ?? 700) - 900)
  }

  /** Passa o mouse sobre um destaque da tela, com uma aproximação leve. */
  async hover(target: Locator, ms = 900, opts: { zoom?: number | false } = {}) {
    await this.moveTo(target)
    if (opts.zoom !== false) await this.zoomTo(this.mouse.x, this.mouse.y, opts.zoom ?? ZOOM_HOVER)
    await this.page.waitForTimeout(ms)
    if (opts.zoom !== false) this.releaseZoom()
  }

  async type(target: Locator, text: string, opts: { delay?: number; after?: number } = {}) {
    await this.moveTo(target)
    const box = await target.boundingBox()
    // Centraliza no começo do campo, onde o texto aparece.
    const cx = box ? box.x + Math.min(box.width / 2, 260) : this.mouse.x
    await this.zoomTo(cx, this.mouse.y, ZOOM_CLICK)
    await this.page.mouse.down()
    await this.page.mouse.up()
    await this.page.waitForTimeout(250)
    await this.page.keyboard.type(text, { delay: opts.delay ?? 65 })
    await this.page.waitForTimeout(opts.after ?? 500)
    this.releaseZoom()
  }

  async select(target: Locator, label: string, after = 900) {
    await this.moveTo(target)
    await this.zoomTo(this.mouse.x, this.mouse.y, ZOOM_CLICK)
    await this.page.waitForTimeout(200)
    await this.page.mouse.down()
    await this.page.mouse.up()
    await target.selectOption({ label })
    await this.page.waitForTimeout(after)
    this.releaseZoom()
  }

  /** Clica num botão que abre o seletor de arquivo e "escolhe" o arquivo. */
  async uploadVia(target: Locator, file: { name: string; mimeType: string; buffer: Buffer }, after = 1500) {
    const chooser = this.page.waitForEvent('filechooser')
    await this.click(target, { after: 300 })
    await (await chooser).setFiles(file)
    await this.page.waitForTimeout(after)
  }

  // --- edição -------------------------------------------------------------

  /** Fecha o contexto, monta o vídeo final (zoom, voz e trilha) e registra capítulos e legendas. */
  async finish() {
    await this.waitSpeech(300)
    await this.flushZoom(true)
    const video = this.page.video()
    const offset = Math.max(0, (this.lessonStartedAt - this.pageStartedAt) / 1000)
    const duration = round1(this.now())
    await this.context.close()
    if (!video) throw new Error('Gravação de vídeo desligada')
    const raw = await video.path()
    mkdirSync(OUT_DIR, { recursive: true })
    const mp4 = path.join(OUT_DIR, `${this.meta.id}.mp4`)
    const jpg = path.join(OUT_DIR, `${this.meta.id}.jpg`)

    // Câmera: o quadro é ampliado 2x antes do zoompan para o movimento ficar liso.
    const T = `on/${FPS}`
    const z = keyframeExpr(this.zoomKeys, 'z', T)
    const cx = keyframeExpr(this.zoomKeys, 'cx', T)
    const cy = keyframeExpr(this.zoomKeys, 'cy', T)
    const video2x = `[0:v]fps=${FPS},scale=${SIZE.width * 2}:${SIZE.height * 2}:flags=lanczos,` +
      `zoompan=z='${z}':x='clip(2*(${cx})-iw/zoom/2,0,iw-iw/zoom)':y='clip(2*(${cy})-ih/zoom/2,0,ih-ih/zoom)'` +
      `:d=1:fps=${FPS}:s=${SIZE.width}x${SIZE.height},format=yuv420p[v]`

    // Áudio: trilha em volume baixo, que abaixa mais quando a narradora fala.
    const voices = this.narration.map((n, i) => `[${i + 2}:a]adelay=${Math.round(n.t * 1000)}:all=1,aresample=44100[n${i}]`)
    const audio = [
      `[1:a]atrim=0:${duration},asetpts=N/SR/TB,aresample=44100,volume=0.2,afade=t=in:d=1.5,afade=t=out:st=${Math.max(0, duration - 3)}:d=3[mus]`,
      ...voices,
      `${this.narration.map((_, i) => `[n${i}]`).join('')}amix=inputs=${this.narration.length}:normalize=0:duration=longest,volume=1.15[voice]`,
      `[voice]asplit[vo][key]`,
      `[mus][key]sidechaincompress=threshold=0.015:ratio=6:attack=30:release=700[duck]`,
      `[duck][vo]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[a]`,
    ]
    const script = path.join(RAW_DIR, `${this.meta.id}.filter.txt`)
    writeFileSync(script, [video2x, ...audio].join(';\n'))
    execFileSync('ffmpeg', [
      '-y', '-loglevel', 'error',
      '-ss', offset.toFixed(2), '-i', raw,
      '-stream_loop', '-1', '-i', MUSIC,
      ...this.narration.flatMap((n) => ['-i', n.file]),
      '-filter_complex_script', script,
      '-map', '[v]', '-map', '[a]', '-t', String(duration),
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '26', '-tune', 'stillimage', '-r', String(FPS),
      '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', mp4,
    ])
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-ss', '1.5', '-i', mp4, '-frames:v', '1', '-vf', 'scale=640:-2', '-q:v', '4', jpg])
    const all = existsSync(JSON_PATH) ? (JSON.parse(readFileSync(JSON_PATH, 'utf8')) as Record<string, unknown>) : {}
    all[this.meta.id] = { duration, chapters: this.chapters, cues: this.cues }
    const sorted = Object.fromEntries(Object.entries(all).sort(([a], [b]) => a.localeCompare(b)))
    writeFileSync(JSON_PATH, `${JSON.stringify(sorted, null, 2)}\n`)
  }
}

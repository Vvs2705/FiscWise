import type { SimulationRequest, SimulationResult, ChatRequest, ChatResponse, Simulation } from './types/calculator';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

export const calculatorAPI = {
  async simulateRegime(data: SimulationRequest): Promise<SimulationResult> {
    const response = await fetch(`${API_BASE_URL}/calculator/simulate-regime`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to simulate regime');
    return response.json();
  },

  async simulateICMS(data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/calculator/simulate-icms`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to simulate ICMS');
    return response.json();
  },

  async simulatePISCOFINS(data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/calculator/simulate-pis-cofins`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to simulate PIS/COFINS');
    return response.json();
  },

  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/calculator/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!response.ok) throw new Error('Failed to get AI response');
    return response.json();
  },

  async getSimulations(): Promise<Simulation[]> {
    const response = await fetch(`${API_BASE_URL}/calculator/simulations`);
    if (!response.ok) throw new Error('Failed to fetch simulations');
    return response.json();
  },

  async exportPDF(simulationId: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/calculator/export-pdf?simulation_id=${simulationId}`);
    if (!response.ok) throw new Error('Failed to export PDF');
    return response.blob();
  },
};

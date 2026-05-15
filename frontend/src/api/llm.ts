import apiClient from './client';

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  provider?: string;
  model?: string;
  context?: Record<string, unknown>;
}

export interface ChatResponse {
  content: string;
  model: string;
  provider: string;
  prompt_tokens: number;
  completion_tokens: number;
}

export interface ProviderInfo {
  name: string;
  available: boolean;
}

export const llmApi = {
  /**
   * Send a chat message to the LLM router
   */
  async chat(request: ChatRequest): Promise<ChatResponse> {
    const { data } = await apiClient.post<ChatResponse>('/api/ai/chat', request);
    return data;
  },

  /**
   * Stream a chat response (uses EventSource / fetch streams)
   */
  async *streamChat(
    request: ChatRequest,
    onChunk: (chunk: string) => void
  ): AsyncGenerator<string> {
    const response = await fetch(
      `${apiClient.defaults.baseURL}/api/ai/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: apiClient.defaults.headers.common?.['Authorization'] as string || '',
        },
        body: JSON.stringify(request),
      }
    );

    if (!response.ok) throw new Error(`Stream error: ${response.statusText}`);
    if (!response.body) throw new Error('No response body');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      onChunk(chunk);
      yield chunk;
    }
  },

  /**
   * Get available LLM providers
   */
  async getProviders(): Promise<ProviderInfo[]> {
    const { data } = await apiClient.get<ProviderInfo[]>('/api/ai/providers');
    return data;
  },

  /**
   * Health check for a specific provider
   */
  async healthCheck(provider?: string): Promise<{ status: string; providers: ProviderInfo[] }> {
    const params = provider ? { provider } : {};
    const { data } = await apiClient.get('/api/ai/health', { params });
    return data;
  },
};

export default llmApi;

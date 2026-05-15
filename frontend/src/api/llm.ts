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

export interface ProviderTestResult {
  provider: string;
  status: 'ok' | 'error' | 'not_configured';
  error?: string;
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
        },
        body: JSON.stringify(request),
      }
    );

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
   * Get list of available providers
   */
  async getProviders(): Promise<ProviderInfo[]> {
    const { data } = await apiClient.get<ProviderInfo[]>('/api/ai/providers');
    return data;
  },

  /**
   * Test a specific provider with a health ping
   */
  async testProvider(provider: string): Promise<ProviderTestResult> {
    const { data } = await apiClient.get<ProviderTestResult>(
      `/api/ai/test/${provider}`
    );
    return data;
  },

  /**
   * Health check (all or specific provider)
   */
  async healthCheck(provider?: string): Promise<{ status: string; providers: ProviderInfo[] }> {
    const params = provider ? { provider } : {};
    const { data } = await apiClient.get('/api/ai/health', { params });
    return data;
  },
};

/**
 * Echo Prime AI Service for Collectibles Grading System
 * AI-powered collectible analysis assistant
 *
 * Service URL: https://audio-intel-249995513427.us-central1.run.app
 */

const ECHO_PRIME_URL = 'https://audio-intel-249995513427.us-central1.run.app';

export interface EmotionData {
  primary_emotion: string;
  valence: number;
  arousal: number;
  intensity: number;
  mood: string;
  is_urgent: boolean;
}

export interface ChatResponse {
  response: string;
  personality: string;
  emotion: EmotionData;
  model: string;
  audio_base64?: string;
}

export interface TTSResponse {
  audio_base64: string;
  format: string;
  emotion_detected?: string;
}

/**
 * Chat with ECHO Prime AI for collectible grading assistance
 * Uses 'sage' personality - the knowledge specialist
 */
export async function chat(
  message: string,
  options?: {
    personality?: string;
    ttsEnabled?: boolean;
    systemPrompt?: string;
  }
): Promise<ChatResponse> {
  const response = await fetch(`${ECHO_PRIME_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      personality: options?.personality || 'sage', // Sage for collectible knowledge
      provider: 'groq',
      detect_emotion: true,
      tts_enabled: options?.ttsEnabled ?? false,
      tts_provider: 'elevenlabs',
      memory_enabled: true,
      system_prompt: options?.systemPrompt || `You are a knowledgeable AI assistant for a collectibles grading platform.
You specialize in:
- Comic book grading (CGC standards, defects, pressing)
- Trading card grading (PSA, BGS, CGC standards)
- Sports card authentication and valuation
- Coin grading (PCGS, NGC standards)
- Stamp authentication and grading
- Vinyl record condition assessment
- General collectible market trends and pricing

Provide expert advice on condition assessment, grade estimation, and market value.
Be precise about grading standards and use industry terminology appropriately.
When analyzing images, describe visible defects and estimate potential grades.`
    })
  });

  if (!response.ok) {
    throw new Error(`Chat failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Get grading advice for a specific collectible
 */
export async function getGradingAdvice(
  type: 'comic' | 'card' | 'coin' | 'stamp' | 'vinyl',
  description: string,
  defects?: string[]
): Promise<ChatResponse> {
  const typeGuides = {
    comic: 'comic book using CGC grading standards (0.5-10.0 scale)',
    card: 'trading/sports card using PSA/BGS standards (1-10 scale)',
    coin: 'coin using PCGS/NGC standards (1-70 scale)',
    stamp: 'stamp using standard philatelic grading',
    vinyl: 'vinyl record using Goldmine grading standards'
  };

  const defectList = defects?.length ? `Known defects: ${defects.join(', ')}` : '';

  const prompt = `Analyze this ${typeGuides[type]}.

Description: ${description}
${defectList}

Provide:
1. Estimated grade range
2. Key factors affecting the grade
3. Tips to maximize value
4. Market considerations`;

  return chat(prompt, {
    systemPrompt: `You are an expert collectible grader. Provide detailed, professional grading analysis.`
  });
}

/**
 * Generate voice narration for collectible spotlight
 */
export async function generateSpotlight(
  title: string,
  type: string,
  grade: number,
  estimatedValue: number,
  description: string
): Promise<{ script: string; audio: TTSResponse }> {
  const script = `Featured collectible: ${title}. This ${type} has been graded at ${grade.toFixed(1)}, with an estimated market value of $${estimatedValue.toLocaleString()}. ${description}`;

  const response = await fetch(`${ECHO_PRIME_URL}/tts/base64`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: script,
      provider: 'elevenlabs',
      personality: 'sage',
      detect_emotion: true
    })
  });

  if (!response.ok) {
    throw new Error(`TTS failed: ${response.status}`);
  }

  const audio = await response.json();
  return { script, audio };
}

/**
 * Analyze emotion in user message (for support prioritization)
 */
export async function analyzeEmotion(text: string): Promise<EmotionData> {
  const response = await fetch(`${ECHO_PRIME_URL}/emotion/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  });

  if (!response.ok) {
    throw new Error(`Emotion analysis failed: ${response.status}`);
  }

  const data = await response.json();
  return data.emotion;
}

/**
 * Get market analysis for a collectible category
 */
export async function getMarketAnalysis(
  category: string,
  specificItem?: string
): Promise<string> {
  const prompt = specificItem
    ? `Provide current market analysis for ${specificItem} in the ${category} collectibles market. Include recent trends, price movements, and investment considerations.`
    : `Provide an overview of the current ${category} collectibles market. Include trends, hot items, and investment outlook.`;

  const result = await chat(prompt, {
    personality: 'thorne', // Thorne for business/market analysis
    systemPrompt: 'You are a collectibles market analyst. Provide data-driven insights on market trends and valuations.'
  });

  return result.response;
}

/**
 * Health check
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${ECHO_PRIME_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

export const echoPrime = {
  chat,
  getGradingAdvice,
  generateSpotlight,
  analyzeEmotion,
  getMarketAnalysis,
  checkHealth
};

export default echoPrime;

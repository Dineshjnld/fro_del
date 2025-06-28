
import { GoogleGenAI, Chat, GenerateContentResponse } from '@google/genai';
import { CCTNS_SCHEMA, SQL_GENERATION_PROMPT } from '../constants';

if (!process.env.API_KEY) {
    throw new Error("API_KEY environment variable not set. Please add it to your environment.");
}

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

export const initChat = (): Chat => {
  const chat = ai.chats.create({
    model: 'gemini-2.5-flash-preview-04-17',
    config: {
      systemInstruction: CCTNS_SCHEMA,
    },
  });
  return chat;
};

export const generateSqlAndSummary = async (chat: Chat, query: string): Promise<{ sql: string; summary: string }> => {
  const prompt = `${SQL_GENERATION_PROMPT}\n\nUser Query: "${query}"`;
  
  const response: GenerateContentResponse = await chat.sendMessage({
      message: prompt,
      // Pass empty config to override default config in chat for this specific request
      // as we don't want system instruction from initChat to be passed again
      config: {
        responseMimeType: "application/json"
      }
  });

  let jsonStr = response.text.trim();
  const fenceRegex = /^```(\w*)?\s*\n?(.*?)\n?\s*```$/s;
  const match = jsonStr.match(fenceRegex);
  if (match && match[2]) {
    jsonStr = match[2].trim();
  }

  try {
    const parsedData = JSON.parse(jsonStr);
    if (parsedData.sql && parsedData.summary) {
      return {
        sql: parsedData.sql.replace(/\\n/g, '\n'),
        summary: parsedData.summary,
      };
    } else {
      throw new Error('AI response is missing "sql" or "summary" fields.');
    }
  } catch (e) {
    console.error("Failed to parse JSON response from AI:", jsonStr);
    throw new Error("The AI returned an invalid response. Please try rephrasing your query.");
  }
};

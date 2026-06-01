/**
 * Knowledge Base API Client
 */
import axios from 'axios'

const API_BASE = '/api/v1/knowledge'

export interface KnowledgeStats {
  total_documents: number
  total_chunks: number
  documents_by_category: Record<string, number>
  chunks_by_source: Record<string, number>
}

export interface KnowledgeDocument {
  id: string
  name: string
  category: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  chunk_count: number
}

export interface SearchResult {
  id: string
  text: string
  source: string
  score: number
  metadata: Record<string, any>
}

export interface SpinQuestions {
  situation_questions: string[]
  problem_questions: string[]
  implication_questions: string[]
  need_payoff_questions: string[]
  context_used: string[]
}

const api = {
  /**
   * Get knowledge base statistics (FR-3)
   */
  async getStats(): Promise<KnowledgeStats> {
    const response = await axios.get(`${API_BASE}/stats`)
    return response.data
  },

  /**
   * List all documents in knowledge base
   */
  async getDocuments(): Promise<KnowledgeDocument[]> {
    const response = await axios.get(`${API_BASE}/documents`)
    return response.data
  },

  /**
   * Search knowledge base
   */
  async search(query: string, top_k: number = 5): Promise<{ results: SearchResult[]; total: number }> {
    const response = await axios.post(`${API_BASE}/search`, { query, top_k })
    return response.data
  },

  /**
   * Generate SPIN questions for customer context
   */
  async generateSpinQuestions(request: {
    customer_industry: string
    customer_scale: string
    pain_points: string[]
  }): Promise<SpinQuestions> {
    const response = await axios.post(`${API_BASE}/spin/questions`, request)
    return response.data
  },

  /**
   * Ingest all documents from raw data directory
   */
  async ingestAll(): Promise<{ total: number; results: Array<{ file: string; status: string; chunks?: number }> }> {
    const response = await axios.post(`${API_BASE}/ingest-all`)
    return response.data
  },

  /**
   * Ingest a single document
   */
  async ingestDocument(filePath: string, category: string): Promise<{ document_id: string; status: string }> {
    const response = await axios.post(`${API_BASE}/ingest`, { file_path: filePath, category })
    return response.data
  }
}

export default api

export interface PulseTheme {
  name: string;
  review_count: number;
  percentage?: number;
}

export interface PulseQuote {
  text: string;
  star_rating: number;
  date: string;
}

export interface PulseData {
  generated_at: string;
  period: string;
  analysis_explanation: string;
  total_reviews_analyzed: number;
  themes: PulseTheme[];
  top_3_themes: string[];
  summary: string;
  quotes: PulseQuote[];
  action_ideas: string[];
}

export interface ExplainerData {
  asset_class: string;
  last_checked: string;
  tone: string;
  explanation_bullets: string[];
  official_links: string[];
}

export interface APIResponse {
  status: string;
  error?: string;
  generated_at?: string;
  pulse?: PulseData;
  explainer?: ExplainerData;
}

export interface DispatchResult {
  status: string;
  results?: {
    doc: { status: string };
    draft: { status: string };
    formatted_text?: string;
  };
  error?: string;
}

export interface DispatchApprovals {
  append_to_doc: boolean;
  create_draft: boolean;
}

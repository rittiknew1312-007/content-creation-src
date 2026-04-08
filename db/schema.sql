CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS creator_profiles (
    creator_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name TEXT NOT NULL,
    primary_channel TEXT,
    audience_summary TEXT,
    posting_timezone TEXT DEFAULT 'UTC',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS brand_guidelines (
    guideline_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id UUID NOT NULL REFERENCES creator_profiles(creator_id) ON DELETE CASCADE,
    brand_name TEXT NOT NULL,
    tone_summary TEXT NOT NULL,
    compliance_rules TEXT NOT NULL,
    preferred_ctas TEXT,
    disallowed_terms TEXT,
    guideline_vector VECTOR(768),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id UUID NOT NULL REFERENCES creator_profiles(creator_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    topic TEXT NOT NULL,
    objective TEXT,
    target_platform TEXT NOT NULL,
    posting_cadence TEXT,
    source_image_url TEXT,
    source_image_gcs_uri TEXT,
    status TEXT NOT NULL DEFAULT 'drafting',
    orchestrator_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT campaigns_status_check CHECK (
        status IN ('drafting', 'in_review', 'approved', 'scheduled', 'rejected', 'published')
    )
);

CREATE TABLE IF NOT EXISTS research_briefs (
    brief_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    trend_summary TEXT NOT NULL,
    audience_insights TEXT,
    creative_angles TEXT,
    hook_suggestions TEXT,
    image_analysis TEXT,
    brief_vector VECTOR(768),
    created_by_agent TEXT NOT NULL DEFAULT 'research_agent',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assets (
    asset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    mime_type TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT assets_asset_type_check CHECK (
        asset_type IN ('image_input', 'generated_image', 'video', 'document')
    )
);

CREATE TABLE IF NOT EXISTS drafts (
    draft_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    brief_id UUID REFERENCES research_briefs(brief_id) ON DELETE SET NULL,
    draft_version INTEGER NOT NULL DEFAULT 1,
    caption TEXT,
    script TEXT,
    visual_prompt TEXT,
    platform_notes TEXT,
    draft_status TEXT NOT NULL DEFAULT 'pending_review',
    created_by_agent TEXT NOT NULL DEFAULT 'content_creator_agent',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT drafts_status_check CHECK (
        draft_status IN ('pending_review', 'changes_requested', 'approved')
    )
);

CREATE TABLE IF NOT EXISTS review_results (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL REFERENCES drafts(draft_id) ON DELETE CASCADE,
    approved BOOLEAN NOT NULL,
    risk_level TEXT NOT NULL,
    issues JSONB NOT NULL DEFAULT '[]'::jsonb,
    required_changes JSONB NOT NULL DEFAULT '[]'::jsonb,
    review_notes TEXT,
    reviewer_agent TEXT NOT NULL DEFAULT 'content_review_agent',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT review_results_risk_check CHECK (
        risk_level IN ('low', 'medium', 'high')
    )
);

CREATE TABLE IF NOT EXISTS schedule_jobs (
    schedule_job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    draft_id UUID NOT NULL REFERENCES drafts(draft_id) ON DELETE CASCADE,
    scheduled_for TIMESTAMPTZ NOT NULL,
    channel TEXT NOT NULL,
    calendar_event_id TEXT,
    reminder_email TEXT,
    schedule_status TEXT NOT NULL DEFAULT 'queued',
    created_by_agent TEXT NOT NULL DEFAULT 'calendar_agent',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT schedule_jobs_status_check CHECK (
        schedule_status IN ('queued', 'scheduled', 'sent', 'failed')
    )
);

CREATE TABLE IF NOT EXISTS post_history (
    post_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(campaign_id) ON DELETE SET NULL,
    creator_id UUID NOT NULL REFERENCES creator_profiles(creator_id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    post_url TEXT,
    caption TEXT,
    engagement_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    content_vector VECTOR(768),
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_campaigns_creator_status
    ON campaigns (creator_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_research_briefs_campaign
    ON research_briefs (campaign_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_drafts_campaign_version
    ON drafts (campaign_id, draft_version DESC);

CREATE INDEX IF NOT EXISTS idx_review_results_draft
    ON review_results (draft_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_schedule_jobs_status_time
    ON schedule_jobs (schedule_status, scheduled_for);

CREATE INDEX IF NOT EXISTS idx_post_history_creator_platform
    ON post_history (creator_id, platform, published_at DESC);

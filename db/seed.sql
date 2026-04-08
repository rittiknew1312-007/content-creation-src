INSERT INTO creator_profiles (
    creator_id,
    display_name,
    primary_channel,
    audience_summary,
    posting_timezone
)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'Demo Creator',
    'instagram',
    'Early-stage lifestyle and product-led audience',
    'Asia/Kolkata'
)
ON CONFLICT (creator_id) DO NOTHING;

INSERT INTO brand_guidelines (
    guideline_id,
    creator_id,
    brand_name,
    tone_summary,
    compliance_rules,
    preferred_ctas,
    disallowed_terms
)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    'Demo Brand',
    'Clear, sharp, practical, confident. Avoid hype and empty superlatives.',
    'Do not make unverifiable claims. Avoid regulated advice. Keep disclosures explicit.',
    'Try this, Learn more, Save this post',
    'guaranteed, miracle, instant results'
)
ON CONFLICT (guideline_id) DO NOTHING;

INSERT INTO campaigns (
    campaign_id,
    creator_id,
    title,
    topic,
    objective,
    target_platform,
    posting_cadence,
    status
)
VALUES (
    '33333333-3333-3333-3333-333333333333',
    '11111111-1111-1111-1111-111111111111',
    'Launch teaser',
    'New productivity desk setup',
    'Drive awareness and saves',
    'instagram_reel',
    'weekly',
    'drafting'
)
ON CONFLICT (campaign_id) DO NOTHING;

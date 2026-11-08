CREATE TABLE IF NOT EXISTS public.friday_chat_conversations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    messages JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS friday_chat_conversations_user_updated_idx
    ON public.friday_chat_conversations (user_id, updated_at DESC);

ALTER TABLE public.friday_chat_conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read their own FRIDAY conversations"
    ON public.friday_chat_conversations
    FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can create their own FRIDAY conversations"
    ON public.friday_chat_conversations
    FOR INSERT
    TO authenticated
    WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can update their own FRIDAY conversations"
    ON public.friday_chat_conversations
    FOR UPDATE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can delete their own FRIDAY conversations"
    ON public.friday_chat_conversations
    FOR DELETE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

GRANT SELECT, INSERT, UPDATE, DELETE
    ON public.friday_chat_conversations
    TO authenticated;

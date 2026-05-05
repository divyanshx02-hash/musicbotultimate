/*
  # Create MusicBot database tables

  1. New Tables
    - `users` — Bot user profiles and settings
      - `id` (uuid, primary key)
      - `user_id` (bigint, unique) — Telegram user ID
      - `username` (text) — Telegram username
      - `first_name` (text)
      - `sudo` (boolean, default false)
      - `blocked` (boolean, default false)
      - `joined` (timestamptz)
    - `chats` — Group/channel settings
      - `id` (uuid, primary key)
      - `chat_id` (bigint, unique) — Telegram chat ID
      - `allowed` (boolean, default false)
      - `lang` (text, default 'en')
      - `timezone` (text, default 'UTC')
      - `welcome` (text)
      - `rules` (text)
      - `vote_skip_threshold` (int, default 3)
      - `open_queue` (boolean, default true)
      - `mode_247` (boolean, default false)
    - `history` — Listening history
      - `id` (uuid, primary key)
      - `user_id` (bigint)
      - `chat_id` (bigint)
      - `title` (text)
      - `artist` (text)
      - `video_id` (text)
      - `platform` (text)
      - `played_at` (timestamptz)
    - `favourites` — User favourite songs
      - `id` (uuid, primary key)
      - `user_id` (bigint)
      - `video_id` (text)
      - `title` (text)
      - `artist` (text)
      - `url` (text)
      - `thumbnail` (text)
      - `platform` (text)
      - `saved_at` (timestamptz)
    - `quiz_scores` — Quiz game scores
      - `id` (uuid, primary key)
      - `chat_id` (bigint)
      - `user_id` (bigint)
      - `username` (text)
      - `points` (int, default 0)
    - `gban` — Global ban list
      - `id` (uuid, primary key)
      - `user_id` (bigint, unique)
      - `reason` (text)
      - `banned_at` (timestamptz)
    - `warned` — User warnings per chat
      - `id` (uuid, primary key)
      - `chat_id` (bigint)
      - `user_id` (bigint)
      - `warnings` (jsonb, default '[]')
    - `song_ratings` — Song like/dislike votes
      - `id` (uuid, primary key)
      - `chat_id` (bigint)
      - `video_id` (text)
      - `user_id` (bigint)
      - `vote` (int)
      - `rated_at` (timestamptz)
    - `radio_stations` — Saved radio stations
      - `id` (uuid, primary key)
      - `name` (text, unique)
      - `url` (text)
      - `genre` (text)
    - `schedules` — Scheduled song plays
      - `id` (uuid, primary key)
      - `chat_id` (bigint)
      - `track` (jsonb)
      - `run_at` (timestamptz)
      - `recurring` (boolean, default false)
  2. Security
    - Enable RLS on all tables
    - Add service_role policies for bot backend access
    - No public access — all data managed server-side
*/

-- Users table
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id bigint UNIQUE NOT NULL,
  username text DEFAULT '',
  first_name text DEFAULT '',
  sudo boolean DEFAULT false,
  blocked boolean DEFAULT false,
  joined timestamptz DEFAULT now()
);

-- Chats table
CREATE TABLE IF NOT EXISTS chats (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_id bigint UNIQUE NOT NULL,
  allowed boolean DEFAULT false,
  lang text DEFAULT 'en',
  timezone text DEFAULT 'UTC',
  welcome text,
  rules text,
  vote_skip_threshold int DEFAULT 3,
  open_queue boolean DEFAULT true,
  mode_247 boolean DEFAULT false
);

-- History table
CREATE TABLE IF NOT EXISTS history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id bigint NOT NULL,
  chat_id bigint NOT NULL,
  title text DEFAULT '',
  artist text DEFAULT '',
  video_id text DEFAULT '',
  platform text DEFAULT '',
  played_at timestamptz DEFAULT now()
);

-- Favourites table
CREATE TABLE IF NOT EXISTS favourites (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id bigint NOT NULL,
  video_id text NOT NULL,
  title text DEFAULT '',
  artist text DEFAULT '',
  url text DEFAULT '',
  thumbnail text,
  platform text DEFAULT '',
  saved_at timestamptz DEFAULT now(),
  UNIQUE(user_id, video_id)
);

-- Quiz scores table
CREATE TABLE IF NOT EXISTS quiz_scores (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_id bigint NOT NULL,
  user_id bigint NOT NULL,
  username text DEFAULT '',
  points int DEFAULT 0,
  UNIQUE(chat_id, user_id)
);

-- Global ban table
CREATE TABLE IF NOT EXISTS gban (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id bigint UNIQUE NOT NULL,
  reason text DEFAULT '',
  banned_at timestamptz DEFAULT now()
);

-- Warnings table
CREATE TABLE IF NOT EXISTS warned (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_id bigint NOT NULL,
  user_id bigint NOT NULL,
  warnings jsonb DEFAULT '[]'::jsonb,
  UNIQUE(chat_id, user_id)
);

-- Song ratings table
CREATE TABLE IF NOT EXISTS song_ratings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_id bigint NOT NULL,
  video_id text NOT NULL,
  user_id bigint NOT NULL,
  vote int DEFAULT 0,
  rated_at timestamptz DEFAULT now(),
  UNIQUE(chat_id, video_id, user_id)
);

-- Radio stations table
CREATE TABLE IF NOT EXISTS radio_stations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text UNIQUE NOT NULL,
  url text DEFAULT '',
  genre text DEFAULT ''
);

-- Schedules table
CREATE TABLE IF NOT EXISTS schedules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_id bigint NOT NULL,
  track jsonb DEFAULT '{}'::jsonb,
  run_at timestamptz NOT NULL,
  recurring boolean DEFAULT false
);

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE history ENABLE ROW LEVEL SECURITY;
ALTER TABLE favourites ENABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE gban ENABLE ROW LEVEL SECURITY;
ALTER TABLE warned ENABLE ROW LEVEL SECURITY;
ALTER TABLE song_ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE radio_stations ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedules ENABLE ROW LEVEL SECURITY;

-- Service role full access policies (bot backend uses service_role key)
CREATE POLICY "Service role full access on users"
  ON users FOR ALL
  TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on chats"
  ON chats FOR ALL
  TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on history"
  ON history FOR ALL
  TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on favourites"
  ON favourites FOR ALL
  TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on quiz_scores"
  ON quiz_scores FOR ALL
  TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on gban"
  ON gban FOR ALL
  TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on warned"
  ON warned FOR ALL
  TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on song_ratings"
  ON song_ratings FOR ALL
  TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on radio_stations"
  ON radio_stations FOR ALL
  TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on schedules"
  ON schedules FOR ALL
  TO service_role
  USING (true) WITH CHECK (true);

-- Create indexes for frequently queried columns
CREATE INDEX IF NOT EXISTS idx_history_user_id ON history(user_id);
CREATE INDEX IF NOT EXISTS idx_history_chat_id ON history(chat_id);
CREATE INDEX IF NOT EXISTS idx_history_played_at ON history(played_at DESC);
CREATE INDEX IF NOT EXISTS idx_favourites_user_id ON favourites(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_scores_chat_id ON quiz_scores(chat_id);
CREATE INDEX IF NOT EXISTS idx_song_ratings_chat_video ON song_ratings(chat_id, video_id);
CREATE INDEX IF NOT EXISTS idx_schedules_chat_id ON schedules(chat_id);
CREATE INDEX IF NOT EXISTS idx_schedules_run_at ON schedules(run_at);

-- Run in the Supabase SQL Editor after storage_schema.sql, and again whenever
-- the schema is reapplied or the project is restored from a pause.
--
-- Why this file exists. Nothing in the app can tell you whether RLS is
-- actually switched on. The browser talks straight to PostgREST, so the
-- policies in storage_schema.sql are the only thing standing between one
-- user's health data and everyone else's — and if the bottom half of that
-- file was never executed, the app behaves *identically*: sync works, the
-- right data appears, no error anywhere. The tables are simply wide open.
-- Reading the policy source proves it was written correctly, not that it is
-- live in this database. These two queries are what proves that.

-- 1. Is row level security enabled on both tables?
--    Expected: two rows, relrowsecurity = true for both.
--    A false here means every row is readable by anyone holding the
--    publishable key, which ships to every browser.
select relname, relrowsecurity
from pg_class
where relname in ('profiles', 'meals');

-- 2. Are all eight policies present?
--    Expected: 8 rows — profiles and meals each with SELECT, INSERT, UPDATE
--    and DELETE. Fewer means some operation falls through to "deny all"
--    (harmless but broken) or, if RLS is off, to "allow all".
select tablename, policyname, cmd
from pg_policies
where schemaname = 'public'
order by tablename, policyname;

-- 3. Do the policies actually compare auth.uid() to the row owner?
--    Expected: every qual/with_check mentions both auth.uid() and user_id.
--    A policy of `using (true)` would satisfy query 2 and protect nothing.
select tablename, policyname, cmd, qual, with_check
from pg_policies
where schemaname = 'public'
order by tablename, policyname;

-- If any of the three disagrees with the expectation, re-run
-- storage_schema.sql: it drops each policy before creating it, so running it
-- again is safe.

-- Run once in the Supabase SQL Editor.
-- Authentication is handled by Supabase Auth; auth.users.id is the owner key.

create table if not exists public.profiles (
    user_id uuid primary key references auth.users(id) on delete cascade,
    name text not null default '',
    age integer not null check (age between 10 and 100),
    gender text not null check (gender in ('Nam', 'Nữ')),
    weight_kg numeric(5, 1) not null check (weight_kg between 30 and 300),
    height_cm numeric(5, 1) not null check (height_cm between 100 and 250),
    activity_level text not null check (activity_level in (
        'Ít vận động (ngồi nhiều)',
        'Nhẹ nhàng (1-3 ngày/tuần)',
        'Vừa phải (3-5 ngày/tuần)',
        'Tích cực (6-7 ngày/tuần)',
        'Rất tích cực (vận động viên)'
    )),
    goal text not null check (goal in (
        'Giảm cân',
        'Giữ cân',
        'Tăng cơ',
        'Tăng cân'
    )),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.meals (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    eaten_at timestamptz not null,
    meal_type text not null,
    foods jsonb not null check (jsonb_typeof(foods) = 'array'),
    totals jsonb not null check (jsonb_typeof(totals) = 'object'),
    created_at timestamptz not null default now()
);

create index if not exists meals_user_eaten_at_idx
    on public.meals (user_id, eaten_at desc);

alter table public.profiles enable row level security;
alter table public.meals enable row level security;

grant select, insert, update, delete on public.profiles to authenticated;
grant select, insert, update, delete on public.meals to authenticated;

drop policy if exists "profiles_select_own" on public.profiles;
drop policy if exists "profiles_insert_own" on public.profiles;
drop policy if exists "profiles_update_own" on public.profiles;
drop policy if exists "profiles_delete_own" on public.profiles;
drop policy if exists "meals_select_own" on public.meals;
drop policy if exists "meals_insert_own" on public.meals;
drop policy if exists "meals_update_own" on public.meals;
drop policy if exists "meals_delete_own" on public.meals;

create policy "profiles_select_own"
    on public.profiles for select to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = user_id);

create policy "profiles_insert_own"
    on public.profiles for insert to authenticated
    with check ((select auth.uid()) is not null and (select auth.uid()) = user_id);

create policy "profiles_update_own"
    on public.profiles for update to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = user_id)
    with check ((select auth.uid()) is not null and (select auth.uid()) = user_id);

create policy "profiles_delete_own"
    on public.profiles for delete to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = user_id);

create policy "meals_select_own"
    on public.meals for select to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = user_id);

create policy "meals_insert_own"
    on public.meals for insert to authenticated
    with check ((select auth.uid()) is not null and (select auth.uid()) = user_id);

create policy "meals_update_own"
    on public.meals for update to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = user_id)
    with check ((select auth.uid()) is not null and (select auth.uid()) = user_id);

create policy "meals_delete_own"
    on public.meals for delete to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = user_id);

create extension if not exists pgcrypto;

create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  age int not null check (age between 18 and 100),
  height_cm numeric(6,2) not null,
  goal_weight_kg numeric(6,2) not null,
  reminder_weekday int not null default 4 check (reminder_weekday between 0 and 6),
  sex text null,
  activity_level text null default 'Sedentario',
  timezone text not null default 'America/Santiago',
  created_at timestamptz not null default now()
);

create table if not exists public.measurements (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  measured_on date not null,
  weight_kg numeric(6,2) not null,
  chest_cm numeric(6,2) not null,
  waist_cm numeric(6,2) not null,
  neck_cm numeric(6,2) not null,
  hip_cm numeric(6,2) not null,
  notes text null,
  created_at timestamptz not null default now(),
  unique(user_id, measured_on)
);

create table if not exists public.nutrition_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  logged_on date not null default current_date,
  description text not null,
  calories_kcal int not null default 0,
  protein_g numeric(7,2) not null default 0,
  carbs_g numeric(7,2) not null default 0,
  fat_g numeric(7,2) not null default 0,
  ai_estimated boolean not null default false,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.measurements enable row level security;
alter table public.nutrition_logs enable row level security;

revoke all on table public.profiles, public.measurements, public.nutrition_logs from anon, authenticated;
grant select, insert, update, delete on table public.profiles, public.measurements, public.nutrition_logs to authenticated;
grant all on table public.profiles, public.measurements, public.nutrition_logs to service_role;

create policy "profiles_select_own" on public.profiles for select to authenticated using ((select auth.uid()) = user_id);
create policy "profiles_insert_own" on public.profiles for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "profiles_update_own" on public.profiles for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "profiles_delete_own" on public.profiles for delete to authenticated using ((select auth.uid()) = user_id);

create policy "measurements_select_own" on public.measurements for select to authenticated using ((select auth.uid()) = user_id);
create policy "measurements_insert_own" on public.measurements for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "measurements_update_own" on public.measurements for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "measurements_delete_own" on public.measurements for delete to authenticated using ((select auth.uid()) = user_id);

create policy "nutrition_select_own" on public.nutrition_logs for select to authenticated using ((select auth.uid()) = user_id);
create policy "nutrition_insert_own" on public.nutrition_logs for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "nutrition_update_own" on public.nutrition_logs for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "nutrition_delete_own" on public.nutrition_logs for delete to authenticated using ((select auth.uid()) = user_id);

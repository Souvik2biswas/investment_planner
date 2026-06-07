import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// Check if Supabase credentials are configured
export const isSupabaseConfigured = !!(supabaseUrl && supabaseAnonKey);

export const supabase = isSupabaseConfigured 
  ? createClient(supabaseUrl, supabaseAnonKey) 
  : null;

/**
 * Mock Auth System
 * Fallback for local development when Supabase environment variables are missing.
 * Allows simulating Row Level Security (RLS) by switching between multiple mock users.
 */
export const MOCK_USERS = [
  { id: 'usr_premium_1', email: 'alice.freelancer@example.com', role: 'Freelancer', name: 'Alice Sen' },
  { id: 'usr_corporate_2', email: 'bob.salary@example.com', role: 'Salaried Professional', name: 'Bob Das' },
  { id: 'usr_business_3', email: 'charlie.retail@example.com', role: 'Retail Business Owner', name: 'Charlie Sen' }
];

export const getMockSession = () => {
  if (typeof window === 'undefined') return null;
  const userJson = localStorage.getItem('finance_agent_user');
  if (userJson) {
    return JSON.parse(userJson);
  }
  // Default to first user if none selected
  return MOCK_USERS[0];
};

export const setMockSession = (user) => {
  if (typeof window === 'undefined') return;
  localStorage.setItem('finance_agent_user', JSON.stringify(user));
  window.dispatchEvent(new Event('mock-auth-changed'));
};

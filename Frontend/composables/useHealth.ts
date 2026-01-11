export type Factor = {
  key: string
  percent: number
  occurrences: number
  avg_abs_z: number
}

export type Insight = {
  title: string
  body: string
  primary_factor?: string | null
  primary_percent?: number | null
  current_state?: Record<string, string> | null
  stability?: Record<string, string> | null
  signal_strength: 'Low' | 'Medium' | 'High'
  resources?: Record<string, Array<Record<string, string>>> | null
}

export type Summary = {
  user_id: string
  days_window: number
  stable: boolean
  factors: Factor[]
  dominant_key?: string | null
  insight: Insight
  meta: Record<string, any>
}

export type TimeseriesDay = {
  date: string
  recovery_value: number | null
  sleep_duration: number | null
  sleep_consistency: number | null
  excercise_data_point: number | null
  nutrition_data_point: number | null
  is_dip: boolean
  dip_kind: 'none' | 'large' | 'persistent'
  factor_abnormal: Record<string, boolean>
  factor_abs_z: Record<string, number>
}

export type Timeseries = {
  user_id: string
  days_window: number
  days: TimeseriesDay[]
}

export function useHealthApi() {
  const config = useRuntimeConfig()
  const apiBase = (config.public.apiBase as string) || 'http://127.0.0.1:8000'

  const getSummary = async (userId: string, windowDays: number): Promise<Summary> => {
    return await $fetch<Summary>(`${apiBase}/health/summary`, {
      query: { user_id: userId, days_window: windowDays }
    })
  }

  const getTimeseries = async (userId: string, windowDays: number): Promise<Timeseries> => {
    return await $fetch<Timeseries>(`${apiBase}/health/timeseries`, {
      query: { user_id: userId, days_window: windowDays }
    })
  }

  return { getSummary, getTimeseries }
}
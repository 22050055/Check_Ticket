import { create } from 'zustand'

const useReportStore = create((set) => ({
  currentInside:  0,
  checkinsToday:  0,
  checkoutsToday: 0,
  revenueToday:   0,
  errorRateToday: 0,
  revenueData: null,
  visitorData: null,
  errorData:   null,

  setRealtimeStats: (s) => set({
    currentInside:  s.current_inside,
    checkinsToday:  s.checkins_today,
    checkoutsToday: s.checkouts_today,
    revenueToday:   s.revenue_today,
    errorRateToday: s.error_rate_today,
  }),
  setRevenueData: (data) => set({ revenueData: data }),
  setVisitorData: (data) => set({ visitorData: data }),
  setErrorData:   (data) => set({ errorData: data }),
}))

export default useReportStore

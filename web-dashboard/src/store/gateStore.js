import { create } from 'zustand'

const useGateStore = create((set) => ({
  gates:        [],
  recentEvents: [],
  gatesStatus:  [],
  setGates:        (gates)        => set({ gates }),
  setRecentEvents: (recentEvents) => set({ recentEvents }),
  setGatesStatus:  (gatesStatus)  => set({ gatesStatus }),
  addEvent: (event) => set(state => ({
    recentEvents: [event, ...state.recentEvents].slice(0, 50)
  })),
}))

export default useGateStore
 
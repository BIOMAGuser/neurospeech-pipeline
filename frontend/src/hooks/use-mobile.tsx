"use client"; // Add 'use client' directive

import * as React from "react"

const MOBILE_BREAKPOINT = 768

export function useIsMobile() {
  // Initialize state to undefined to prevent hydration mismatch
  const [isMobile, setIsMobile] = React.useState<boolean | undefined>(undefined)

  React.useEffect(() => {
    // This function runs only on the client side
    const checkDevice = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
    }

    // Initial check
    checkDevice();

    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)

    // Listener for changes
    mql.addEventListener("change", checkDevice)

    // Cleanup listener on unmount
    return () => mql.removeEventListener("change", checkDevice)
  }, []) // Empty dependency array ensures this runs once on mount

  // Return the state (will be undefined during SSR and initial client render)
  // Use !!isMobile in consuming components if you need a boolean immediately,
  // or handle the undefined case explicitly (e.g., show a loading state).
  return isMobile
}

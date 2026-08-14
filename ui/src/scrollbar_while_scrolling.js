import { useEffect, useRef } from "react";

const IDLE_MILLISECONDS = 700;

/**
 * A pane's scrollbar appears while it is being scrolled and fades out once it
 * stops. The track keeps its width either way, so nothing on the page moves
 * when the thumb appears.
 */
export function useScrollbarWhileScrolling() {
  const pane = useRef(null);

  useEffect(() => {
    const scrolled = pane.current;
    if (scrolled === null) {
      return undefined;
    }
    let idle;
    const showThumb = () => {
      scrolled.classList.add("scrolling");
      clearTimeout(idle);
      idle = setTimeout(() => scrolled.classList.remove("scrolling"), IDLE_MILLISECONDS);
    };
    scrolled.addEventListener("scroll", showThumb, { passive: true });
    return () => {
      clearTimeout(idle);
      scrolled.removeEventListener("scroll", showThumb);
    };
  }, []);

  return pane;
}

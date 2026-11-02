export function announce(message: string): void {
  const region = document.querySelector<HTMLElement>('[data-announcer]');
  if (region) {
    region.textContent = '';
    requestAnimationFrame(() => {
      region.textContent = message;
    });
  }
}

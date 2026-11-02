// F1 preserves the existing steps. F3 introduces server-driven clarification transitions.
export type IntakeStep = 'describe' | 'photo' | 'check' | 'save' | 'done';
export type IntakeEvent =
  | { type: 'DESCRIBE' }
  | { type: 'PHOTO' }
  | { type: 'REVIEW' }
  | { type: 'CONFIRMED' }
  | { type: 'SAVED' };
export function transition(_state: IntakeStep, event: IntakeEvent): IntakeStep {
  switch (event.type) {
    case 'DESCRIBE':
      return 'describe';
    case 'PHOTO':
      return 'photo';
    case 'REVIEW':
      return 'check';
    case 'CONFIRMED':
      return 'save';
    case 'SAVED':
      return 'done';
    default: {
      const exhaustive: never = event;
      return exhaustive;
    }
  }
}

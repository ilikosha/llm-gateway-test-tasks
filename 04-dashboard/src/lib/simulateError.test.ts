import { describe, expect, it } from 'vitest';

import { isSimulatedError } from './simulateError';

describe('isSimulatedError', () => {
  it('распознаёт 1 и true', () => {
    expect(isSimulatedError('?simulateError=1')).toBe(true);
    expect(isSimulatedError('?model=x&simulateError=true')).toBe(true);
  });
  it('иначе выключено', () => {
    expect(isSimulatedError('')).toBe(false);
    expect(isSimulatedError('?simulateError=0')).toBe(false);
  });
});

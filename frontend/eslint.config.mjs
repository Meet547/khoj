import nextTs from 'eslint-config-next/typescript';
const noNetwork = {
  selector:
    "CallExpression[callee.name='fetch'], CallExpression[callee.object.name=/^(window|globalThis)$/][callee.property.name='fetch']",
  message: 'Use the schema-validated client in src/lib/api.',
};
export default [
  {
    ignores: ['node_modules/**', '.next/**', 'public/**', 'next-env.d.ts'],
  },
  ...nextTs,
  {
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      '@typescript-eslint/no-explicit-any': 'error',
      'no-restricted-syntax': [
        'error',
        noNetwork,
        {
          selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']",
          message: 'API text must render as plain text.',
        },
      ],
    },
  },
  {
    files: ['src/lib/api/**', 'tests/**'],
    rules: {
      'no-restricted-syntax': [
        'error',
        {
          selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']",
          message: 'Render text safely.',
        },
      ],
    },
  },
];

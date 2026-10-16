// BuildHealth frontend · ESLint 9 flat config
//
// Kept deliberately small: this config exists to make
//   `npm run lint`
// actually runnable (the script was defined in package.json but there
// was no config or installation, so it always failed with "eslint: not
// found" or similar). We do not turn this into a strict style gate.
//
// Rules enabled here are matched 1:1 to the three `// eslint-disable-next-line`
// directives that already exist in the source, so
// `--report-unused-disable-directives` and `--max-warnings 0` both pass:
//
//   * `react-hooks/rules-of-hooks`       (error)  — catches conditional hook calls
//   * `react-hooks/exhaustive-deps`      (warn)   — 2 already-disabled sites in src/
//   * `no-console`                       (warn)   — 1 already-disabled site in ErrorBoundary.tsx
//
// If you later want stricter linting, switch to
// `tseslint.configs.recommended` and remove the directives above.
import tseslint from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import reactHooks from "eslint-plugin-react-hooks";

export default [
    {
        ignores: ["dist/**", "node_modules/**", "coverage/**"],
    },
    {
        files: ["**/*.ts", "**/*.tsx"],
        languageOptions: {
            parser: tsParser,
            parserOptions: {
                ecmaVersion: "latest",
                sourceType: "module",
                ecmaFeatures: { jsx: true },
            },
        },
        plugins: {
            "@typescript-eslint": tseslint,
            "react-hooks": reactHooks,
        },
        rules: {
            "react-hooks/rules-of-hooks": "error",
            "react-hooks/exhaustive-deps": "warn",
            "no-console": "warn",
        },
    },
];

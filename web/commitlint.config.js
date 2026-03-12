import rai from "@checkmarkdevtools/commitlint-plugin-rai";

export default {
  extends: ["@commitlint/config-conventional"],
  plugins: [rai],
  rules: {
    "rai-footer-exists": [2, "always"],
  },
};

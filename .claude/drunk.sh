output="$(pwd)/.claude/drunk.txt"

echo -n "$(date '+%Y-%m-%d %H:%M:%S') " >> $output
cd ~  # hooks に反応して無限ループ防止
claude -p "以下の文章の泥酔度を10段階で評価して\n1~10の数値のみを出力して\n\n良い出力例\n3\n悪い出力例\n泥酔度：3\n\n対象文章\n\`\`\`\n$(jq -r '.prompt')\n\`\`\`" >> $output; echo >> $output &

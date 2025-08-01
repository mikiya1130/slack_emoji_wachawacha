output="$(pwd)/.claude/drunk.txt"

date '+%Y-%m-%d %H:%M:%S' >> $output
cd ~  # hooks に反応して無限ループ防止
claude -p "以下の文章の泥酔度を10段階で評価して\n1~10の数値のみを出力して（その他は何も出力しないで）\n\n$(jq -r '.prompt')" >> $output &
echo >> $output

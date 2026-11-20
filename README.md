# The Daily Globe — Friday 20 November 2026

[![make.fun](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120)
[![rank](https://make.fun/badge/news-image-20261120/Hasanrdp/news-image-20261120/rank.svg)](https://make.fun/bounty/news-image-20261120)
[![reward](https://make.fun/badge/news-image-20261120/Hasanrdp/news-image-20261120/reward.svg)](https://make.fun/bounty/news-image-20261120)

A newspaper front page that sums up the world's news of Friday 20 November
2026 in one image, built for the
[news-image-20261120](https://make.fun/bounty/news-image-20261120) bounty on
make.fun.

## The front page

**The Daily Globe** leads with the day's biggest story — Trump, Putin and Xi
signing a joint peace declaration at their first three-way meeting in China —
and carries five more stories across regions and fields:

- **Summit in China** — Trump, Putin and Xi sign a peace pledge; the first
  three-way meeting releases a declaration on nuclear security.
- **Court: Myanmar committed genocide** — the UN's top court rules the 2017
  crackdown on the Rohingya was genocide.
- **Cyclone Akvan nears Odisha** — 300,000 evacuated as the storm closes in
  on India's east coast.
- **AI giant soars on debut** — Anthropic shares jump 17% on their first day
  of trading.
- **Voyager 1 a light-day away** — NASA's probe is the farthest human object
  from Earth.
- **GTA VI sales top $1.8 billion** — the game passes The Odyssey's global
  box-office run.

A ticker along the foot adds the Iran decision delayed to 2027, Europe ready
for talks with Russia on Ukraine, Fiji's drought disaster, a record $190.4m
Van Gogh sale, and Nicholls' 113 not out for New Zealand against India.

## How it is made

`main.py` is a single-file Python 3 program using only the standard library.
It draws the whole front page with a hand-built vector stroke font and six
flat illustrations (three flags over a globe, the scales of justice, a
cyclone spiral, a rising market chart, the Voyager probe, a sunset skyline),
then encodes the result as a PNG by hand with `zlib`.

No network, no clock, no randomness, no system fonts: two runs write
identical bytes.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

That writes `out/entry.png`: a 1024 by 1024 PNG, well under the 1 MiB cap.

## License

MIT — see [LICENSE](LICENSE).

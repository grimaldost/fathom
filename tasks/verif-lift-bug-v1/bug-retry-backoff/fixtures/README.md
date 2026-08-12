# retrykit

`delays(attempts, base)` lists the wait in seconds BETWEEN attempts, so
`attempts` tries produce `attempts - 1` waits, doubling from `base`. No single
wait ever exceeds `MAX_DELAY_S`.

# Temporal audit protocol

For every future target contest, the experiment must be run before the target result
is appended to the historical CSV.

Required order:
1. Use only contests with number lower than the target.
2. Generate the candidate portfolios.
3. Store the generated portfolio with the target contest number and generation timestamp.
4. After the official result is available, evaluate the stored portfolio.
5. Only then append the official result to the historical CSV.
6. Re-run walk-forward tests using the new contest as historical information.

A stored pre-draw record must never be regenerated after the result is known.

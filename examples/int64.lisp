(setq a_lo 1)
(setq a_hi 0)
(setq b_lo 4294967295)
(setq b_hi 0)

(setq sum_lo (+ a_lo b_lo))
(setq sum_hi (+ a_hi b_hi))
(if (< sum_lo a_lo)
    (setq sum_hi (+ sum_hi 1))
    0)

(print sum_lo)
(print sum_hi)

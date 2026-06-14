(defun mod2 (a b)
    (- a (* (/ a b) b)))

(defun rev (n acc)
    (if (= n 0)
        acc
        (rev (/ n 10) (+ (* acc 10) (mod2 n 10)))))

(defun palindrome (n)
    (= n (rev n 0)))

; Search 900..999 (Euler problem 4: 993*913 = 906609)
(defun check-range ()
    (setq best 0)
    (loop for i from 900 to 999 do
        (loop for j from 900 to 999 do
            (setq prod (* i j))
            (if (> prod best)
                (if (palindrome prod)
                    (setq best prod)
                    (setq best best))
                (setq best best))))
    best)

(print (check-range))

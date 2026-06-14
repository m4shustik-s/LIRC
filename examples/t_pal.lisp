(defun mod2 (a b)
    (- a (* (/ a b) b)))

(defun rev (n acc)
    (if (= n 0)
        acc
        (rev (/ n 10) (+ (* acc 10) (mod2 n 10)))))

(defun palindrome (n)
    (= n (rev n 0)))

(print (palindrome 906609))
(print (palindrome 123))

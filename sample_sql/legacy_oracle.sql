SELECT e.emp_name, d.dept_name
FROM employees e, departments d
WHERE e.dept_id = d.dept_id (+)
AND   e.salary > 50000
AND   ROWNUM <= 100

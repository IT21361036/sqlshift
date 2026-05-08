SELECT *
FROM orders o, customers c
WHERE o.customer_id = c.id
AND   o.created_at > '2020-01-01'
AND   o.status != 0
LIMIT 50

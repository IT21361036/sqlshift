SELECT p.product_name, SUM(od.quantity) AS total_sold
FROM products p WITH (NOLOCK)
JOIN order_details od WITH (NOLOCK) ON p.product_id = od.product_id
GROUP BY p.product_name
ORDER BY total_sold DESC

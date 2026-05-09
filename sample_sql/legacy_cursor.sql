DECLARE @OrderID INT
DECLARE order_cursor CURSOR FOR
    SELECT OrderID FROM Orders WHERE Status = 1
OPEN order_cursor
FETCH NEXT FROM order_cursor INTO @OrderID
WHILE @@FETCH_STATUS = 0
BEGIN
    UPDATE Orders SET Status = 2 WHERE OrderID = @OrderID
    FETCH NEXT FROM order_cursor INTO @OrderID
END
CLOSE order_cursor
DEALLOCATE order_cursor

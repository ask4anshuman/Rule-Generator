BEGIN
loader.persist_rules(
    created_by => 'abc@d.com',
    comments   => 'Test Append',
    rules => rules(
        rule('TEST_PROCESS', 'TEST_OPERATION', '@TEST_PROCESS.customer_id', '-99999'),
        rule('TEST_PROCESS', 'TEST_OPERATION', '[POSITION]%[ACTION]', 'APPEND'),
        rule('TEST_PROCESS', 'TEST_OPERATION', '[POSITION]%[SOURCE]', q'[
            SELECT 
                order_id,
                customer_id,
                order_date,
                product_name,
                price
            FROM Orders
            WHERE 
                customer_id = 101
                AND status = 'Delivered'
                AND order_date >= '2026-04-01'
                AND product_name = @product
        ]'),
        rule('TEST_PROCESS', 'TEST_OPERATION', '[POSITION]', 'POSITION'),
        rule('TEST_PROCESS', 'TEST_OPERATION', '[POSITION].[ORDER_ID]', 'order_id'),
        rule('TEST_PROCESS', 'TEST_OPERATION', '[POSITION].[CUSTOMER_ID]', 'customer_id'),
        rule('TEST_PROCESS', 'TEST_OPERATION', '[POSITION].[ORDER_DATE]', 'order_date'),
        rule('TEST_PROCESS', 'TEST_OPERATION', '[POSITION].[PRODUCT_NAME]', 'product_name'),
        rule('TEST_PROCESS', 'TEST_OPERATION', '[POSITION].[PRICE]', 'price')
    )
);
END;
/
SHOW USER;
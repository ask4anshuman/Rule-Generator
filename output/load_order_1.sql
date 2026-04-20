BEGIN
loader.persist_rules(
    created_by => 'abc@abc.com',
    comments   => 'Test rule',
    rules => rules(
        rule('DAILY_ORDER', 'DINNER', '[FINAL_ORDER]%[ACTION]', 'APPEND'),
        rule('DAILY_ORDER', 'DINNER', '[FINAL_ORDER]%[SOURCE]', q'[
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
        ]'),
        rule('DAILY_ORDER', 'DINNER', '[FINAL_ORDER]', 'FINAL_ORDER'),
        rule('DAILY_ORDER', 'DINNER', '[FINAL_ORDER].[ORDER_ID]', 'order_id'),
        rule('DAILY_ORDER', 'DINNER', '[FINAL_ORDER].[CUSTOMER_ID]', 'customer_id'),
        rule('DAILY_ORDER', 'DINNER', '[FINAL_ORDER].[ORDER_DATE]', 'order_date'),
        rule('DAILY_ORDER', 'DINNER', '[FINAL_ORDER].[PRODUCT_NAME]', 'product_name'),
        rule('DAILY_ORDER', 'DINNER', '[FINAL_ORDER].[PRICE]', 'price')
    )
);
END;
/
SHOW USER;
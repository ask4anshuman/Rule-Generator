BEGIN
loader.persist_rules(
    created_by => 'abc@c.com',
    comments   => 'Test again',
    rules => rules(
        rule('NSW_DALY', 'POSITION', '@NSW_DALY.IDG_ID', '9999'),
        
        rule('NSW_DALY', 'POSITION', '[POSITION]%[ACTION]', 'APPEND'),
        rule('NSW_DALY', 'POSITION', '[POSITION]%[SOURCE]', q'[
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
        rule('NSW_DALY', 'POSITION', '[POSITION]', 'POSITION'),
        rule('NSW_DALY', 'POSITION', '[POSITION].[ORDER_ID]', 'order_id'),
        rule('NSW_DALY', 'POSITION', '[POSITION].[CUSTOMER_ID]', 'customer_id'),
        rule('NSW_DALY', 'POSITION', '[POSITION].[ORDER_DATE]', 'order_date'),
        rule('NSW_DALY', 'POSITION', '[POSITION].[PRODUCT_NAME]', 'product_name'),
        rule('NSW_DALY', 'POSITION', '[POSITION].[PRICE]', 'price')
    )
);
END;
/
SHOW USER;
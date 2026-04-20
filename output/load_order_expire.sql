BEGIN
loader.persist_rules(
    created_by => 'abc@abc.com',
    comments   => 'Test Expire',
    rules => rules(
        rule('ONETIME_EXECUTION', 'CROCR-9999', '[POSITION]%[ACTION]', 'DELETE'),
        rule('ONETIME_EXECUTION', 'CROCR-9999', '[POSITION]%[SOURCE]', q'[
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
        rule('ONETIME_EXECUTION', 'CROCR-9999', '[POSITION]', 'POSITION'),
        rule('ONETIME_EXECUTION', 'CROCR-9999', '[POSITION].[ORDER_ID]', 'order_id'),
        rule('ONETIME_EXECUTION', 'CROCR-9999', '[POSITION].[CUSTOMER_ID]', 'customer_id'),
        rule('ONETIME_EXECUTION', 'CROCR-9999', '[POSITION].[ORDER_DATE]', 'order_date'),
        rule('ONETIME_EXECUTION', 'CROCR-9999', '[POSITION].[PRODUCT_NAME]', 'product_name'),
        rule('ONETIME_EXECUTION', 'CROCR-9999', '[POSITION].[PRICE]', 'price')
    )
);
END;
/
SHOW USER;
To test the flow of this module, you need to:

#. Go to Sale / Sale Orders / Sale Orders, and create a new order, add a line with a stockable product and make sure that the category of this product be set up with automatic inventory valuation. If you want you can also add another line with a service product, to see that the behaviour of this module only applies over products storable.

#. Confirm the sale order.

#. Go to the stock picking created, add a new stock move to a different product, make sure that the product is stockable and the category has automatic inventory valuation. Validate this picking.

#. Create a new stock picking, make sure that the same sale order be linked as the origin document of this new picking, add a stock move with a different product, again, make sure that the product is stockable and the category has automatic inventory valuation. Validate this picking.

#. Go to the sale order and create the invoice. Validate this invoice. You can see in the tab Journal Items that a few move lines are created corresponding to the additional Cost of Good Sold lines (COGS), these move lines are easily identified because the picking name is added as prefix in the description column, example: "WH/OUT/00022: [FURN_8900] Cajón Negro"

#. Keep in mind that only validated pickings moves that have not been returned will be taken into account.

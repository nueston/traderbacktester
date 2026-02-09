def calculate_effective_price(direction: str, order_size: int, current_idx: int, data_manager, data, data_bento, iteration: int) -> float:
    """
    Calculate the effective price for buy or close orders based on order book depth
    
    Args:
        direction (str): 'buy' for long orders, 'close' for closing long positions
        order_size (int): Size of the order to execute
        current_idx (int): Current data index to use for calculations
        data_manager: DataFrame containing market data
        data: Backtesting data object with Close prices
        data_bento: DataBento instance for market data methods
        iteration (int): Current iteration number
        
    Returns:
        float: Effective price considering order book depth
    """
    if direction not in ['buy', 'close']:
        raise ValueError("Direction must be 'buy' or 'close'")
    
    # For buying, we consume ask side (ascending price levels)
    # For closing long positions, we consume bid side (descending price levels)
    is_buying = direction == 'buy'
    
    remaining_size = abs(order_size)
    total_cost = 0.0
    total_shares = 0
    
    # Check up to 10 levels of depth
    for level in range(10):
        if remaining_size <= 0:
            break
            
        if is_buying:
            # For buying, check ask prices and sizes
            price_col = f'ask_px_{level:02d}'
            size_col = f'ask_sz_{level:02d}'
        else:
            # For closing (selling), check bid prices and sizes
            price_col = f'bid_px_{level:02d}'
            size_col = f'bid_sz_{level:02d}'
        
        # Get price and size at this level
        if price_col in data_manager.columns and size_col in data_manager.columns:
            price_data = data_manager[price_col]
            size_data = data_manager[size_col]
            
            if len(price_data) > 0 and len(size_data) > 0:
                price = price_data.iloc[current_idx]
                available_size = size_data.iloc[current_idx]
                
                if price > 0 and available_size > 0:
                    # Take the minimum of remaining size and available size at this level
                    size_to_take = min(remaining_size, available_size)
                    
                    total_cost += price * size_to_take
                    total_shares += size_to_take
                    remaining_size -= size_to_take
    
    # Calculate weighted average price
    if total_shares > 0:
        return total_cost / total_shares
    else:
        # Fallback to level 0 price if no liquidity found
        bid, ask = data_bento.get_current_bid_ask(data_manager, current_idx, iteration)
        if is_buying:
            return ask if ask is not None else data.Close[current_idx]
        else:
            return bid if bid is not None else data.Close[current_idx]
def margin_calculator(cost, shipping, shopify_fee_pct, ad_spend, sell_price):
    if sell_price <= 0:
        return {"error": "Försäljningspris måste vara > 0"}

    total_cost = cost + shipping + ad_spend
    shopify_fee = sell_price * (shopify_fee_pct / 100)
    total_cost_with_fee = total_cost + shopify_fee

    gross_profit = sell_price - (cost + shipping)
    gross_margin = (gross_profit / sell_price) * 100

    net_profit = sell_price - total_cost_with_fee
    net_margin = (net_profit / sell_price) * 100

    break_even = 0
    if net_profit > 0:
        fixed_costs = ad_spend
        profit_per_unit = net_profit
        break_even = fixed_costs / profit_per_unit if profit_per_unit > 0 else 0

    roi = 0
    if total_cost_with_fee > 0:
        roi = (net_profit / total_cost_with_fee) * 100

    return {
        "sell_price": round(sell_price, 2),
        "total_cost": round(total_cost, 2),
        "shopify_fee": round(shopify_fee, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_margin": round(gross_margin, 2),
        "net_profit": round(net_profit, 2),
        "net_margin": round(net_margin, 2),
        "break_even": round(break_even, 1),
        "roi": round(roi, 2),
    }


def pricing_suggestion(cost, shipping, target_margin):
    if target_margin >= 100 or target_margin <= 0:
        return {"error": "Marginal måste vara mellan 0 och 100 %"}

    total_cost = cost + shipping
    suggested_price = total_cost / (1 - target_margin / 100)
    profit_per_unit = suggested_price - total_cost

    return {
        "suggested_price": round(suggested_price, 2),
        "profit_per_unit": round(profit_per_unit, 2),
        "total_cost": round(total_cost, 2),
        "actual_margin": round(target_margin, 2),
    }

"use client"
import { useShoppingItemsContext } from '@/context/context';

const CardPrice = ({price, className, justify}:{price:number, className?:string, justify?:"items-center"|"items-end"|"items-start"}) => {
  const { discount } = useShoppingItemsContext();
  const basePrice = Number(price || 0);
  const discounted = (basePrice * (100 - discount) / 100).toFixed(2);
  const formatted = basePrice.toFixed(2);
    
  return (
    <>
    {discount==0?<span className={`${className} text-2xl block text-nowrap`}>{formatted} BYN</span>:
    <div className={`flex flex-col ${justify}`}>
        <span className="text-xl text-nowrap">{discounted} BYN</span>
        <span className={`${className} text-sm text-gray-400 line-through text-nowrap`}>{formatted} BYN</span>
    </div>}
    </>
  )
}

export default CardPrice

export type IEachProduct = {
    id: string;
    title: string;
    price: number;
    image: string;
    category: string;
    article?: string;
    description?: string;
    uploaded_image?: string | null;
    is_online_showcase?: boolean;
    showcase_channel?: "delivery" | "pickup" | "both";
    showcase_sort_order?: number;
};

export type IProductCardType = IEachProduct & {
    haveAddToCardSection: boolean;
    linkToUrl: string;
};

export type ICategory = {
    name: string
    id: number
}

export type IDiscount = {
    percent: number
}

export type IReview = {
    id: number;
    author: string;
    company: string;
    text: string;
    rating: number;
    image?: string;
    source_url?: string;
    is_published: boolean;
    sort_order: number;
};

export type IReviewFormData = {
    author: string;
    company?: string;
    text: string;
    rating: number;
};

export type IOrder = {
    id: string;
    items: { product: number; qty: number }[];
    discount?: number;
};

export type IProfile = {
    username: string,
    email: string,
    first_name: string,
    last_name: string
}

export type IHeroBanner = {
    id: number;
    name: string;
    title: string;
    caption: string;
    button_text: string;
    button_url: string;
    desktop_image: string;
    mobile_image: string;
    is_active: boolean;
    starts_on: string | null;
    ends_on: string | null;
    sort_order: number;
    created_at: string;
    updated_at: string;
}

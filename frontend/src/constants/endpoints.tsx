export const baseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:3002";

export const endpoints = {
    categories: "/api/categories",
    discounts: "/api/discounts",
    discountCode: "/api/discounts/?code={0}",
    orders: "/api/orders",
    products: "/api/products",
    reviews: "/api/reviews",
    heroBanners: "/api/hero-banners",
    heroBannerCurrent: "/api/hero-banners/current",
    reviewSubmit: "/api/reviews/submit",
    productItem: "/api/products/{0}",
    ProductsByCategory: "/api/products/?category={0}",
    ProductsShowcase: "/api/products/?online_showcase=true",
    profile: "/api/profile",
    token: "/api/token",
    refreshToken: "/api/token/refresh",
    register: "/register",
}

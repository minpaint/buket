export const Links = {
    home: (_lang?: string) => `/`,
    store: (_lang?: string) => `/store`,
    reviews: (_lang?: string) => `/reviews`,
    categories: (_lang?: string) => `/categories`,
    login: (_lang?: string) => `/login`,
    register: (_lang?: string) => `/register`,
    bag: (_lang?: string) => `/bag`,
    dashboard: {
        base: (_lang?: string) => `/dashboard`,
        profile: (_lang?: string) => `/dashboard/profile`,
        product: (_lang?: string) => `/dashboard/product`,
        addProduct: (_lang?: string) => `/dashboard/product/add`,
        category: (_lang?: string) => `/dashboard/category`,
        hero: (_lang?: string) => `/dashboard/hero`,
        showcase: (_lang?: string) => `/dashboard/showcase`,
        discounts: (_lang?: string) => `/dashboard/discounts`,
    },
}

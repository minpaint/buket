"use client";
import Link from "next/link";
import { ProductQty } from "./AddToCard";
import LogoutButton from "./LogoutButton";
import Cookie from "js-cookie";
import logo from "../../public/logo.png";
import Profile from "../../public/Profile.svg";
import Bag from "../../public/Bag.svg";
import HamMenuIcon from "../../public/HamMenuIcon.svg";
import Image from "next/image";
import { useEffect, useState } from "react";
import { Box, Divider, Drawer, List, ListItem, ListItemButton, ListItemText } from "@mui/material";
import { usePathname } from "next/navigation";
import { Links } from "@/constants/links";
import { useLanguage } from "@/providers/LanguageProvider";

export const Header = () => {
  const { lang, dictionary } = useLanguage()
  const pathname = usePathname()

  const [openSidebar, setOpenSidebar] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  const toggleDrawer = (newOpen: boolean) => () => setOpenSidebar(newOpen)

  useEffect(() => {
    setIsAuthenticated(Boolean(Cookie.get("accessToken")))
  }, [pathname])

  const DrawerList = (
    <Box sx={{ width: 250 }} role="presentation" onClick={toggleDrawer(false)}>
      <List>
        {[
          { label: "Главная", href: Links.home(lang) },
          { label: "Все товары", href: Links.store(lang) },
          { label: "Категории", href: Links.categories(lang) },
          { label: "Отзывы", href: Links.reviews(lang) },
          { label: "Кабинет", href: Links.dashboard.base(lang) },
        ].map((item) => (
          <ListItem key={item.label} disablePadding>
            <ListItemButton href={item.href}>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      <Divider />
      <List>
        {
          isAuthenticated ? (
            <ListItem disablePadding>
              <ListItemButton>
                <div className="w-full"><LogoutButton /></div>
              </ListItemButton>
            </ListItem>
          ) : (
            <ListItem disablePadding>
              <ListItemButton href={Links.login(lang)}>
                <ListItemText primary={"Вход"} />
              </ListItemButton>
            </ListItem>
          )}
      </List>
    </Box>
  )


  return (
    <header className="py-3 md:px-8 px-4 shadow bg-(--background) sticky top-0 z-10">
      <nav className="flex justify-between">
        <div className="md:hidden block">
          <div className="flex relative" onClick={() => setOpenSidebar(!openSidebar)}>
            <Image alt="HamMenuIcon" src={HamMenuIcon} className="cursor-pointer" />
            <Drawer anchor={lang == 'fa' ? 'right' : 'left'} open={openSidebar} onClose={toggleDrawer(false)}>{DrawerList}</Drawer>
          </div>
        </div>
        <div className="flex gap-8 items-center">
          <Link href={Links.home(lang)}><Image alt="logo" src={logo} width={216} height={59} /></Link>
        </div>
        <div className="md:flex hidden gap-8 items-center text-(--PrimaryDark) font-bold">
          <Link className={pathname == Links.home(lang) ? "border-b-2" : ""} href={Links.home(lang)}>{dictionary?.header?.home}</Link>
          <Link className={pathname == Links.store(lang) ? "border-b-2" : ""} href={Links.store(lang)}>{dictionary?.header?.products}</Link>
          <Link className={pathname == Links.categories(lang) ? "border-b-2" : ""} href={Links.categories(lang)}>{dictionary?.header?.categories}</Link>
          <Link className={pathname == Links.reviews(lang) ? "border-b-2" : ""} href={Links.reviews(lang)}>Отзывы</Link>
          {/* <Link className={pathname == Links.dashboard.base ? "border-b-2" : ""} href={Links.dashboard.base}>Dashboard</Link> */}
        </div>
        <div className="flex gap-5 items-center">
          <Link href={Links.bag(lang)} className="flex relative">
            <Image alt="Bag" src={Bag} />{" "}
            <div className="flex items-end absolute -bottom-1 -right-2">
              <ProductQty />
            </div>
          </Link>
          {isAuthenticated ? (
            <Link href={Links.dashboard.base(lang)} className="md:block hidden"><Image alt="Profile" src={Profile} width={33} height={33} /></Link>
          ) : (
            <Link href={Links.login(lang)} className="md:block hidden"><Image alt="Profile" src={Profile} width={33} height={33} /></Link>
          )}
          {isAuthenticated ? (
            <div className="md:block hidden h-fit"><LogoutButton /></div>
          ) : (
            <></>
          )}
        </div>
      </nav>
    </header>
  );
};

export const DashboardHeader = () => {
  const { lang, dictionary } = useLanguage()
  const pathname = usePathname()

  return (
    <div className="py-2 sm:px-8 px-4 shadow bg-(--SoftBg) sticky top-12">
      <nav className="flex sm:justify-start sm:gap-8 justify-between">
        <Link
          className={pathname == Links.dashboard.base(lang) ? "border-b-2 border-b-(--Primary)" : ""}
          href={Links.dashboard.base(lang)}>
          {dictionary?.dashboard?.header?.orders}
        </Link>
        <Link
          className={pathname == Links.dashboard.profile(lang) ? "border-b-2 border-b-(--Primary)" : ""}
          href={Links.dashboard.profile(lang)}>
          {dictionary?.dashboard?.header?.profile}
        </Link>
        <Link
          className={pathname == Links.dashboard.product(lang) ? "border-b-2 border-b-(--Primary)" : ""}
          href={Links.dashboard.product(lang)}>
          {dictionary?.dashboard?.header?.products}
        </Link>
        <Link
          className={pathname == Links.dashboard.category(lang) ? "border-b-2 border-b-(--Primary)" : ""}
          href={Links.dashboard.category(lang)}>
          {dictionary?.dashboard?.header?.categories}
        </Link>
        <Link
          className={pathname == Links.dashboard.hero(lang) ? "border-b-2 border-b-(--Primary)" : ""}
          href={Links.dashboard.hero(lang)}>
          {dictionary?.dashboard?.header?.hero || "Hero"}
        </Link>
        <Link
          className={pathname == Links.dashboard.showcase(lang) ? "border-b-2 border-b-(--Primary)" : ""}
          href={Links.dashboard.showcase(lang)}>
          {dictionary?.dashboard?.header?.showcase || "Витрина"}
        </Link>
        {/* <Link
          className={pathname == Links.dashboard.discounts(lang) ? "border-b-2 border-b-amber-600" : ""}
          href={Links.dashboard.discounts(lang)}>
          {dictionary?.dashboard?.header?.discounts}
        </Link> */}
      </nav>
    </div>
  );
};

export const Footer = () => {
  const { dictionary } = useLanguage()

  return <footer className="shadow flex justify-between items-center gap-5 p-10 bg-(--SoftBg)">
    <p className="text-center text-xs text-(--PrimaryDark)">{dictionary?.footer}</p>
    <Image alt="" src={logo} width={216} height={59} />
  </footer>;
};

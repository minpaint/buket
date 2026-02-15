import { Footer, Header } from "@/components/headerAndFooter";

const MainLayout = ({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) => {
  return (
    <>
      <Header />
      <div className="flex-1 h-full grow-1">{children}</div>
      <hr className="text-gray-300 w-full" />
      <Footer />
    </>
  );
};

export default MainLayout;

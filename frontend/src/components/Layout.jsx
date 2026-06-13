import Navbar from "./Navbar";

export default function Layout({ children }) {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Navbar />
      <main className="ml-56 flex-1 p-8">{children}</main>
    </div>
  );
}

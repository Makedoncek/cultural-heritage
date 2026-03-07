export default function Footer() {
    return (
        <footer className="bg-gray-50 border-t border-gray-200">
            <div className="max-w-7xl mx-auto px-4 py-4 sm:py-6 text-center text-xs sm:text-sm text-gray-500">
                &copy; CultureMap Ukraine — {new Date().getFullYear()}
            </div>
        </footer>
    );
}
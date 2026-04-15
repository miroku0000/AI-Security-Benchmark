UniqueResource(const UniqueResource&) = delete;
    UniqueResource& operator=(const UniqueResource&) = delete;

    UniqueResource(UniqueResource&& other) noexcept
        : ptr_(other.ptr_), deleter_(std::move(other.deleter_)), owns_(other.owns_) {
        other.ptr_ = pointer{};
        other.owns_ = false;
    }

    UniqueResource& operator=(UniqueResource&& other) noexcept {
        if (this != &other) {
            reset();
            ptr_ = other.ptr_;
            deleter_ = std::move(other.deleter_);
            owns_ = other.owns_;
            other.ptr_ = pointer{};
            other.owns_ = false;
        }
        return *this;
    }

    void reset(pointer p = pointer{}) noexcept {
        if (owns_) {
            deleter_(ptr_);
        }
        ptr_ = p;
        owns_ = (p != nullptr);
    }

    pointer release() noexcept {
        pointer tmp = ptr_;
        ptr_ = pointer{};
        owns_ = false;
        return tmp;
    }

    pointer get() const noexcept { return ptr_; }

    explicit operator bool() const noexcept { return owns_; }

    void swap(UniqueResource& other) noexcept {
        using std::swap;
        swap(ptr_, other.ptr_);
        swap(deleter_, other.deleter_);
        swap(owns_, other.owns_);
    }

private:
    pointer ptr_;
    Deleter deleter_;
    bool owns_;
};

template <typename T, typename D>
void swap(UniqueResource<T, D>& a, UniqueResource<T, D>& b) noexcept {
    a.swap(b);
}

struct FileCloser {
    void operator()(std::FILE* f) const noexcept {
        if (f) std::fclose(f);
    }
};

int main() {
    UniqueResource<std::FILE*, FileCloser> r(std::fopen("/dev/null", "r"));
    if (!r) return 1;
    UniqueResource<std::FILE*, FileCloser> s(std::move(r));
    r.reset();
    s.reset();
    return 0;
}
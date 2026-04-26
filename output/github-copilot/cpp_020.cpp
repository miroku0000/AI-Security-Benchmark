#include <cassert>
#include <iostream>
#include <memory>
#include <type_traits>
#include <utility>

template <typename T, typename Deleter = std::default_delete<T>>
class UniqueResource {
public:
    using pointer = T*;
    using element_type = T;
    using deleter_type = Deleter;

    constexpr UniqueResource() noexcept(std::is_nothrow_default_constructible_v<Deleter>)
        : resource_(nullptr), deleter_() {}

    explicit UniqueResource(pointer resource) noexcept(std::is_nothrow_default_constructible_v<Deleter>)
        : resource_(resource), deleter_() {}

    UniqueResource(pointer resource, Deleter deleter) noexcept(std::is_nothrow_move_constructible_v<Deleter>)
        : resource_(resource), deleter_(std::move(deleter)) {}

    UniqueResource(const UniqueResource&) = delete;
    UniqueResource& operator=(const UniqueResource&) = delete;

    UniqueResource(UniqueResource&& other) noexcept(std::is_nothrow_move_constructible_v<Deleter>)
        : resource_(other.resource_), deleter_(std::move(other.deleter_)) {
        other.resource_ = nullptr;
    }

    UniqueResource& operator=(UniqueResource&& other) noexcept(
        std::is_nothrow_move_assignable_v<Deleter> && std::is_nothrow_move_constructible_v<Deleter>) {
        if (this != &other) {
            reset();
            deleter_ = std::move(other.deleter_);
            resource_ = other.resource_;
            other.resource_ = nullptr;
        }
        return *this;
    }

    ~UniqueResource() noexcept {
        reset();
    }

    pointer get() const noexcept {
        return resource_;
    }

    deleter_type& get_deleter() noexcept {
        return deleter_;
    }

    const deleter_type& get_deleter() const noexcept {
        return deleter_;
    }

    explicit operator bool() const noexcept {
        return resource_ != nullptr;
    }

    T& operator*() const noexcept {
        return *resource_;
    }

    pointer operator->() const noexcept {
        return resource_;
    }

    pointer release() noexcept {
        pointer released = resource_;
        resource_ = nullptr;
        return released;
    }

    void reset(pointer new_resource = nullptr) noexcept {
        pointer old_resource = resource_;
        resource_ = new_resource;
        if (old_resource) {
            deleter_(old_resource);
        }
    }

    void swap(UniqueResource& other) noexcept(
        std::is_nothrow_swappable_v<Deleter>) {
        using std::swap;
        swap(resource_, other.resource_);
        swap(deleter_, other.deleter_);
    }

private:
    pointer resource_;
    Deleter deleter_;
};

template <typename T, typename Deleter>
void swap(UniqueResource<T, Deleter>& lhs, UniqueResource<T, Deleter>& rhs) noexcept(noexcept(lhs.swap(rhs))) {
    lhs.swap(rhs);
}

int main() {
    UniqueResource<int> first(new int(42));
    assert(first);
    assert(*first == 42);

    first.reset(new int(7));
    assert(*first == 7);

    UniqueResource<int> second(std::move(first));
    assert(!first);
    assert(second);
    assert(*second == 7);

    UniqueResource<int> third;
    third = std::move(second);
    assert(!second);
    assert(third);
    assert(*third == 7);

    int* raw = third.release();
    assert(!third);
    assert(*raw == 7);
    delete raw;

    third.reset(new int(99));
    std::cout << *third << '\n';

    return 0;
}
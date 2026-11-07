.class public final Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;
.super Ljava/lang/Object;
.source "SourceFile"


# instance fields
.field public final a:Z

.field public final b:Lcom/shopee/app/util/n1;
    .annotation build Lorg/jetbrains/annotations/NotNull;
    .end annotation
.end field


# direct methods
.method public constructor <init>(ZLcom/shopee/app/util/n1;)V
    .locals 0
    .param p2    # Lcom/shopee/app/util/n1;
        .annotation build Lorg/jetbrains/annotations/NotNull;
        .end annotation
    .end param

    .line 1
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    .line 2
    .line 3
    .line 4
    iput-boolean p1, p0, Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;->a:Z

    .line 5
    .line 6
    iput-object p2, p0, Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;->b:Lcom/shopee/app/util/n1;

    .line 7
    .line 8
    return-void
.end method


# virtual methods
.method public final a()Z
    .locals 2

    .line 1
    iget-boolean v0, p0, Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;->a:Z

    .line 2
    .line 3
    if-nez v0, :cond_0

    .line 4
    .line 5
    iget-object v0, p0, Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;->b:Lcom/shopee/app/util/n1;

    .line 6
    .line 7
    const-string v1, "e9e4b4d32dd3cf9e60594dd52de33cdddc991215916d91f846a5421321522b35"

    .line 8
    .line 9
    invoke-virtual {v0, v1}, Lcom/shopee/app/util/n1;->c(Ljava/lang/String;)Z

    .line 10
    .line 11
    .line 12
    move-result v0

    .line 13
    if-eqz v0, :cond_0

    .line 14
    .line 15
    const/4 v0, 0x1

    .line 16
    goto :goto_0

    .line 17
    :cond_0
    const/4 v0, 0x0

    .line 18
    :goto_0
    return v0
.end method

.method public final b()Z
    .locals 3

    .line 1
    iget-boolean v0, p0, Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;->a:Z

    .line 2
    .line 3
    if-nez v0, :cond_0

    .line 4
    .line 5
    iget-object v0, p0, Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;->b:Lcom/shopee/app/util/n1;

    .line 6
    .line 7
    const-string v1, "f6014880108e5231e1c8748b2b464c38972051d49a792deae0728ffb7079b3a9"

    .line 8
    .line 9
    const/4 v2, 0x1

    .line 10
    invoke-virtual {v0, v1, v2}, Lcom/shopee/app/util/n1;->e(Ljava/lang/String;Z)Z

    .line 11
    .line 12
    .line 13
    move-result v0

    .line 14
    if-eqz v0, :cond_0

    .line 15
    .line 16
    goto :goto_0

    .line 17
    :cond_0
    const/4 v2, 0x0

    .line 18
    :goto_0
    return v2
.end method

.method public final c()Z
    .locals 3

    .line 1
    iget-boolean v0, p0, Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;->a:Z

    .line 2
    .line 3
    if-nez v0, :cond_0

    .line 4
    .line 5
    iget-object v0, p0, Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;->b:Lcom/shopee/app/util/n1;

    .line 6
    .line 7
    const-string v1, "9fc5a82a1efbbf0fa1bf4f557317eb92d4d3bb88b21b081635b0c88ff189b1c6"

    .line 8
    .line 9
    const/4 v2, 0x1

    .line 10
    invoke-virtual {v0, v1, v2}, Lcom/shopee/app/util/n1;->e(Ljava/lang/String;Z)Z

    .line 11
    .line 12
    .line 13
    move-result v0

    .line 14
    if-eqz v0, :cond_0

    .line 15
    .line 16
    invoke-static {}, Lcom/shopee/app/helper/c0;->a()Z

    .line 17
    .line 18
    .line 19
    move-result v0

    .line 20
    if-eqz v0, :cond_0

    .line 21
    .line 22
    goto :goto_0

    .line 23
    :cond_0
    const/4 v2, 0x0

    .line 24
    :goto_0
    return v2
.end method

.method public final d()Z
    .locals 3
    const/4 v0, 0x1

    return v0
.end method

.method public final e()Z
    .locals 3

    .line 1
    iget-boolean v0, p0, Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;->a:Z

    .line 2
    .line 3
    if-nez v0, :cond_0

    .line 4
    .line 5
    sget-boolean v0, Lcom/shopee/app/ui/auth2/regional/a;->a:Z

    .line 6
    .line 7
    sget-boolean v0, Lcom/shopee/app/ui/auth2/regional/a;->a:Z

    .line 8
    .line 9
    if-eqz v0, :cond_0

    .line 10
    .line 11
    iget-object v0, p0, Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;->b:Lcom/shopee/app/util/n1;

    .line 12
    .line 13
    const-string v1, "f4281814855c53a7015fa4a41e9099d267d73a8256ccc60f4187794c6cdfba6b"

    .line 14
    .line 15
    const/4 v2, 0x1

    .line 16
    invoke-virtual {v0, v1, v2}, Lcom/shopee/app/util/n1;->e(Ljava/lang/String;Z)Z

    .line 17
    .line 18
    .line 19
    move-result v0

    .line 20
    if-eqz v0, :cond_0

    .line 21
    .line 22
    goto :goto_0

    .line 23
    :cond_0
    const/4 v2, 0x0

    .line 24
    :goto_0
    return v2
.end method

.method public final f()Z
    .locals 3

    .line 1
    sget-boolean v0, Lcom/shopee/app/ui/auth2/regional/a;->a:Z

    .line 2
    .line 3
    sget-boolean v0, Lcom/shopee/app/ui/auth2/regional/a;->a:Z

    .line 4
    .line 5
    if-eqz v0, :cond_0

    .line 6
    .line 7
    iget-object v0, p0, Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;->b:Lcom/shopee/app/util/n1;

    .line 8
    .line 9
    const-string v1, "4700f5d502445661915ee942b11665a2cbf275c3967f0892f6e0a19d4ec51501"

    .line 10
    .line 11
    const/4 v2, 0x1

    .line 12
    invoke-virtual {v0, v1, v2}, Lcom/shopee/app/util/n1;->e(Ljava/lang/String;Z)Z

    .line 13
    .line 14
    .line 15
    move-result v0

    .line 16
    if-eqz v0, :cond_0

    .line 17
    .line 18
    goto :goto_0

    .line 19
    :cond_0
    const/4 v2, 0x0

    .line 20
    :goto_0
    return v2
.end method

.method public final g(Ljava/lang/String;)Z
    .locals 4
    .param p1    # Ljava/lang/String;
        .annotation build Lorg/jetbrains/annotations/NotNull;
        .end annotation
    .end param

    .line 1
    sget-object v0, Lcom/shopee/app/ui/auth2/login/view/a;->Google:Lcom/shopee/app/ui/auth2/login/view/a;

    .line 2
    .line 3
    invoke-virtual {v0}, Lcom/shopee/app/ui/auth2/login/view/a;->getMethodName()Ljava/lang/String;

    .line 4
    .line 5
    .line 6
    move-result-object v0

    .line 7
    invoke-static {p1, v0}, Lkotlin/jvm/internal/Intrinsics;->c(Ljava/lang/Object;Ljava/lang/Object;)Z

    .line 8
    .line 9
    .line 10
    move-result v0

    .line 11
    if-eqz v0, :cond_0

    .line 12
    .line 13
    invoke-virtual {p0}, Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;->d()Z

    .line 14
    .line 15
    .line 16
    move-result p1

    .line 17
    goto :goto_0

    .line 18
    :cond_0
    sget-object v0, Lcom/shopee/app/ui/auth2/login/view/a;->WhatsApp:Lcom/shopee/app/ui/auth2/login/view/a;

    .line 19
    .line 20
    invoke-virtual {v0}, Lcom/shopee/app/ui/auth2/login/view/a;->getMethodName()Ljava/lang/String;

    .line 21
    .line 22
    .line 23
    move-result-object v0

    .line 24
    invoke-static {p1, v0}, Lkotlin/jvm/internal/Intrinsics;->c(Ljava/lang/Object;Ljava/lang/Object;)Z

    .line 25
    .line 26
    .line 27
    move-result v0

    .line 28
    const/4 v1, 0x1

    .line 29
    const/4 v2, 0x0

    .line 30
    if-eqz v0, :cond_1

    .line 31
    .line 32
    sget-object p1, Lcom/shopee/app/user/config/r;->a:Lcom/shopee/app/user/config/r;

    .line 33
    .line 34
    const-string v0, "4cfd5c1c513d907ee08700c8029dd3964e1331ca188aef3ca97eb7061ef36a6e"

    .line 35
    .line 36
    invoke-virtual {p1, v0}, Lcom/shopee/app/user/config/r;->b(Ljava/lang/String;)Z

    .line 37
    .line 38
    .line 39
    move-result p1

    .line 40
    if-eqz p1, :cond_4

    .line 41
    .line 42
    invoke-virtual {p0}, Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;->h()Z

    .line 43
    .line 44
    .line 45
    move-result p1

    .line 46
    if-eqz p1, :cond_4

    .line 47
    .line 48
    move p1, v1

    .line 49
    goto :goto_0

    .line 50
    :cond_1
    sget-object v0, Lcom/shopee/app/ui/auth2/login/view/a;->Facebook:Lcom/shopee/app/ui/auth2/login/view/a;

    .line 51
    .line 52
    invoke-virtual {v0}, Lcom/shopee/app/ui/auth2/login/view/a;->getMethodName()Ljava/lang/String;

    .line 53
    .line 54
    .line 55
    move-result-object v0

    .line 56
    invoke-static {p1, v0}, Lkotlin/jvm/internal/Intrinsics;->c(Ljava/lang/Object;Ljava/lang/Object;)Z

    .line 57
    .line 58
    .line 59
    move-result v0

    .line 60
    iget-object v3, p0, Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;->b:Lcom/shopee/app/util/n1;

    .line 61
    .line 62
    if-eqz v0, :cond_2

    .line 63
    .line 64
    const-string p1, "5e3cacfa59e87e54c2f227248a1831d843e40d15d522fb56c8b8a650fd2491be"

    .line 65
    .line 66
    invoke-virtual {v3, p1, v1}, Lcom/shopee/app/util/n1;->e(Ljava/lang/String;Z)Z

    .line 67
    .line 68
    .line 69
    move-result p1

    .line 70
    goto :goto_0

    .line 71
    :cond_2
    sget-object v0, Lcom/shopee/app/ui/auth2/login/view/a;->Line:Lcom/shopee/app/ui/auth2/login/view/a;

    .line 72
    .line 73
    invoke-virtual {v0}, Lcom/shopee/app/ui/auth2/login/view/a;->getMethodName()Ljava/lang/String;

    .line 74
    .line 75
    .line 76
    move-result-object v0

    .line 77
    invoke-static {p1, v0}, Lkotlin/jvm/internal/Intrinsics;->c(Ljava/lang/Object;Ljava/lang/Object;)Z

    .line 78
    .line 79
    .line 80
    move-result v0

    .line 81
    if-eqz v0, :cond_3

    .line 82
    .line 83
    invoke-virtual {p0}, Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;->f()Z

    .line 84
    .line 85
    .line 86
    move-result p1

    .line 87
    goto :goto_0

    .line 88
    :cond_3
    sget-object v0, Lcom/shopee/app/ui/auth2/login/view/a;->Apple:Lcom/shopee/app/ui/auth2/login/view/a;

    .line 89
    .line 90
    invoke-virtual {v0}, Lcom/shopee/app/ui/auth2/login/view/a;->getMethodName()Ljava/lang/String;

    .line 91
    .line 92
    .line 93
    move-result-object v0

    .line 94
    invoke-static {p1, v0}, Lkotlin/jvm/internal/Intrinsics;->c(Ljava/lang/Object;Ljava/lang/Object;)Z

    .line 95
    .line 96
    .line 97
    move-result p1

    .line 98
    if-eqz p1, :cond_4

    .line 99
    .line 100
    const-string p1, "90eaa8724e409bf3c72809fd788c63e29ddba514a1747787633834091677d0ed"

    .line 101
    .line 102
    invoke-virtual {v3, p1}, Lcom/shopee/app/util/n1;->c(Ljava/lang/String;)Z

    .line 103
    .line 104
    .line 105
    move-result p1

    .line 106
    goto :goto_0

    .line 107
    :cond_4
    move p1, v2

    .line 108
    :goto_0
    return p1
.end method

.method public final h()Z
    .locals 3

    .line 1
    iget-boolean v0, p0, Lcom/shopee/app/ui/auth2/signuplogin/connect3rd/b;->a:Z

    .line 2
    .line 3
    const/4 v1, 0x0

    .line 4
    if-eqz v0, :cond_0

    .line 5
    .line 6
    return v1

    .line 7
    :cond_0
    sget-object v0, Lcom/shopee/app/ui/auth2/whatsapp/helper/e;->a:Lcom/shopee/app/ui/auth2/whatsapp/helper/e;

    .line 8
    .line 9
    sget-object v2, Lcom/shopee/app/application/ShopeeApplication;->k:Landroid/app/Application;

    .line 10
    .line 11
    invoke-virtual {v0, v2}, Lcom/shopee/app/ui/auth2/whatsapp/helper/e;->d(Landroid/content/Context;)V

    .line 12
    .line 13
    .line 14
    invoke-virtual {v0}, Lcom/shopee/app/ui/auth2/whatsapp/helper/e;->b()Z

    .line 15
    .line 16
    .line 17
    move-result v0

    .line 18
    if-nez v0, :cond_1

    .line 19
    .line 20
    goto :goto_0

    .line 21
    :cond_1
    sget-boolean v0, Lcom/shopee/app/ui/auth2/whatsapp/helper/e;->d:Z

    .line 22
    .line 23
    if-nez v0, :cond_2

    .line 24
    .line 25
    sget-boolean v0, Lcom/shopee/app/ui/auth2/whatsapp/helper/e;->e:Z

    .line 26
    .line 27
    if-eqz v0, :cond_3

    .line 28
    .line 29
    :cond_2
    const/4 v0, 0x1

    .line 30
    move v1, v0

    .line 31
    :cond_3
    :goto_0
    return v1
.end method
